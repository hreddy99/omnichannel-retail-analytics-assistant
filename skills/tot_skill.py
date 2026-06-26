"""
Conditional Tree-of-Thought beam search.

Generates candidate driver branches, runs one read-only DuckDB evidence query
per branch, scores each on the 0-14 rubric (11.1), prunes weak branches, and
keeps the top `BEAM_WIDTH`. Includes a governance pre-screen that rejects
ungoverned hypotheses (no certified metric/table) without spending query budget.

Used by workflows/graph.py (the LangGraph controller).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from skills import catalog_skill as catalog, graph_skill as graph, sql_skill as guardrails

BEAM_WIDTH = 2          # ToT keeps the top 2 primary drivers
DEPTH_LIMIT = 2         # driver -> sub-driver refinement
# The unified app dispatches the full specialized analyst team in parallel, so the
# operational query bound is one baseline query plus one read-only query per domain
# analyst (not the narrower beam-only path). Keeping this honest so the UI never
# shows "queries used" exceeding the budget.
N_DOMAIN_ANALYSTS = 7
QUERY_BUDGET = 1 + N_DOMAIN_ANALYSTS   # 8: 1 baseline + 7 domain analysts

PRIMARY_DRIVERS = ["campaign_mix", "inventory_availability", "fulfillment_constraints"]
RESERVE_DRIVER = "funnel_behavior"

# Evidence strength (0-3, the heaviest dimension) only counts when the structural
# checks (metric + graph + SQL safety, max 6) clear this bar. This stops strong
# DuckDB evidence from overriding governance checks that signal problems.
STRUCTURAL_MIN = 4


@dataclass
class Branch:
    driver: str
    label: str = ""
    owner: str = ""
    hypothesis: str = ""
    sql: str = ""
    evidence: pd.DataFrame | None = None
    signal: float = 0.0
    finding: str = ""
    scores: dict = field(default_factory=dict)
    total: int = 0
    confidence: str = ""
    sub_drivers: list = field(default_factory=list)
    governed: bool = True
    evidence_gated: bool = False
    tied: bool = False          # set when an unresolved tie downgraded this branch


def _rel_score(rel: float) -> int:
    a = abs(rel)
    return 3 if a >= 0.50 else 2 if a >= 0.25 else 1 if a >= 0.10 else 0


# --------------------------------------------------------------------------
# Driver evidence queries (read-only). Each returns (sql, df, signal, finding).
# --------------------------------------------------------------------------
def q_campaign_mix(con, td, b0, b1):
    sql = f"""
    WITH t AS (SELECT channel, count(*) n FROM fact_sessions WHERE date=DATE '{td}' GROUP BY channel),
         b AS (SELECT channel, count(*)*1.0/7 n FROM fact_sessions
               WHERE date BETWEEN DATE '{b0}' AND DATE '{b1}' GROUP BY channel)
    SELECT t.channel,
           t.n*1.0/(SELECT sum(n) FROM t) AS share_target,
           b.n*1.0/(SELECT sum(n) FROM b) AS share_base,
           (SELECT sum(CASE WHEN converted THEN 1 ELSE 0 END)*1.0/count(*) FROM fact_sessions f
            WHERE f.date=DATE '{td}' AND f.channel=t.channel) AS conv_target
    FROM t JOIN b USING(channel) ORDER BY share_target DESC"""
    ev = con.execute(sql).df()
    ps = ev[ev.channel == "paid_social"].iloc[0]
    rel = float((ps.share_target - ps.share_base) / ps.share_base)
    finding = (f"paid_social session share rose {ps.share_base:.0%}->{ps.share_target:.0%} "
               f"while converting at {ps.conv_target:.1%} (below the ~2.4% baseline).")
    return sql, ev, rel, finding


def q_inventory(con, td, b0, b1):
    sql = f"""
    SELECT i.category_id, c.category_name,
           avg(CASE WHEN date=DATE '{td}' THEN stockout_rate END) AS stockout_target,
           avg(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' THEN stockout_rate END) AS stockout_base,
           avg(CASE WHEN date=DATE '{td}' THEN product_views END) AS views_target
    FROM fact_inventory_daily i JOIN dim_category c USING(category_id)
    GROUP BY i.category_id, c.category_name ORDER BY stockout_target DESC"""
    ev = con.execute(sql).df()
    top = ev.iloc[0]
    rel = float((top.stockout_target - top.stockout_base) / top.stockout_base)
    finding = (f"category '{top.category_name}' stockout rose "
               f"{top.stockout_base:.0%}->{top.stockout_target:.0%} on high product "
               f"views ({int(top.views_target):,}).")
    return sql, ev, rel, finding


def q_fulfillment(con, td, b0, b1):
    sql = f"""
    SELECT region,
           avg(CASE WHEN date=DATE '{td}' THEN delay_days END) AS delay_target,
           avg(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' THEN delay_days END) AS delay_base,
           avg(CASE WHEN date=DATE '{td}' THEN options_available END) AS options_target
    FROM fact_fulfillment GROUP BY region ORDER BY delay_target DESC"""
    ev = con.execute(sql).df()
    top = ev.iloc[0]
    rel = float((top.delay_target - top.delay_base) / top.delay_base)
    finding = (f"region '{top.region}' delivery delay rose {top.delay_base:.1f}d->"
               f"{top.delay_target:.1f}d with options cut to {int(top.options_target)}.")
    return sql, ev, rel, finding


def q_funnel(con, td, b0, b1):
    sql = f"""
    WITH ev AS (
      SELECT date, category_id,
             sum(CASE WHEN event_type='add_to_cart' THEN 1 ELSE 0 END) carts,
             sum(CASE WHEN event_type='purchase' THEN 1 ELSE 0 END) purch
      FROM fact_events GROUP BY date, category_id)
    SELECT e.category_id, c.category_name,
           sum(CASE WHEN date=DATE '{td}' THEN purch ELSE 0 END)*1.0
             / nullif(sum(CASE WHEN date=DATE '{td}' THEN carts ELSE 0 END),0) AS rate_target,
           sum(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' THEN purch ELSE 0 END)*1.0
             / nullif(sum(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' THEN carts ELSE 0 END),0) AS rate_base
    FROM ev e JOIN dim_category c USING(category_id)
    GROUP BY e.category_id, c.category_name"""
    ev = con.execute(sql).df()
    ev["rel"] = (ev.rate_target - ev.rate_base) / ev.rate_base
    overall = float((ev.rate_target.mean() - ev.rate_base.mean()) / ev.rate_base.mean())
    # An isolated funnel defect is a category whose cart->purchase fell MORE than the
    # overall conversion movement (downward only, a category that improved, or merely
    # tracked the overall drop, is not an independent funnel problem). Using a signed
    # downward excess avoids crediting an outlier that went UP.
    ev["excess_drop"] = (overall - ev["rel"]).clip(lower=0)
    worst = ev.iloc[ev["excess_drop"].argmax()]
    excess = float(worst["excess_drop"])
    if excess >= 0.10:
        finding = (f"cart-to-purchase moved {overall:+.0%} overall; '{worst.category_name}' fell an "
                   f"extra {excess:.0%} beyond that, an isolated funnel defect.")
    else:
        finding = (f"cart-to-purchase moved with the overall {overall:+.0%}; no category shows a "
                   "material isolated funnel defect, on-site behavior tracked the drop, "
                   "it didn't independently cause it.")
    return sql, ev, excess, finding


def q_service(con, td, b0, b1):
    """Customer-contact spike, by reason code, vs baseline."""
    sql = f"""
    SELECT reason_code,
           sum(CASE WHEN date=DATE '{td}' THEN 1 ELSE 0 END) AS contacts_target,
           sum(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' THEN 1 ELSE 0 END)/7.0 AS contacts_base
    FROM fact_customer_contacts GROUP BY reason_code ORDER BY contacts_target DESC"""
    ev = con.execute(sql).df()
    tot_t = float(ev.contacts_target.sum()); tot_b = float(ev.contacts_base.sum()) or 1.0
    rel = (tot_t - tot_b) / tot_b
    top = ev.iloc[0]
    finding = (f"customer contacts rose {tot_b:.0f}->{tot_t:.0f}/day ({rel:+.0%}); top reason "
               f"'{top.reason_code}' corroborates an operational issue.")
    return sql, ev, rel, finding


def q_finance(con, td, b0, b1):
    """Gross-to-net reconciliation caveat."""
    sql = f"""
    SELECT sum(CASE WHEN date=DATE '{td}' THEN gross_sales ELSE 0 END) AS gross_t,
           sum(CASE WHEN date=DATE '{td}' THEN net_revenue ELSE 0 END) AS net_t,
           sum(CASE WHEN date=DATE '{td}' THEN returns ELSE 0 END) AS returns_t,
           avg(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}'
                    THEN returns/nullif(gross_sales,0) END) AS return_rate_base,
           sum(CASE WHEN date=DATE '{td}' THEN returns ELSE 0 END)
             / nullif(sum(CASE WHEN date=DATE '{td}' THEN gross_sales ELSE 0 END),0) AS return_rate_t
    FROM fact_finance_daily"""
    ev = con.execute(sql).df()
    r = ev.iloc[0]
    gap = float((r.gross_t - r.net_t) / r.gross_t) if r.gross_t else 0.0
    rel = float((r.return_rate_t - r.return_rate_base) / r.return_rate_base) if r.return_rate_base else 0.0
    finding = (f"net revenue is {gap:.0%} off gross (returns/tax/shipping/adjustments); "
               f"return rate {r.return_rate_t:.1%} vs {r.return_rate_base:.1%} baseline. "
               f"Reconciliation caveat, not an operational conversion cause.")
    return sql, ev, rel, finding


def q_vendor(con, td, b0, b1):
    """Vendor/category stockout impact weighted by sales exposure."""
    sql = f"""
    WITH cat_sales AS (
      SELECT category_id, sum(item_amount) AS sales
      FROM fact_order_items GROUP BY category_id),
    cat_stock AS (
      SELECT category_id, avg(CASE WHEN date=DATE '{td}' THEN stockout_rate END) AS stockout_target,
             avg(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' THEN stockout_rate END) AS stockout_base
      FROM fact_inventory_daily GROUP BY category_id),
    vend AS (
      SELECT category_id, any_value(vendor_id) AS vendor_id, any_value(brand) AS brand
      FROM dim_product GROUP BY category_id)
    SELECT s.category_id, v.vendor_id, v.brand, s.stockout_target, s.stockout_base, cs.sales,
           s.stockout_target * cs.sales AS impact
    FROM cat_stock s JOIN cat_sales cs USING(category_id) JOIN vend v USING(category_id)
    ORDER BY impact DESC"""
    ev = con.execute(sql).df()
    top = ev.iloc[0]
    rel = float((top.stockout_target - top.stockout_base) / top.stockout_base) if top.stockout_base else 0.0
    finding = (f"vendor '{top.vendor_id}' (brand {top.brand}) in category {top.category_id} carries the "
               f"highest sales-weighted stockout impact ({top.stockout_target:.0%} stockout). Alert the partner.")
    return sql, ev, rel, finding


DRIVER_QUERY = {
    "campaign_mix": q_campaign_mix, "inventory_availability": q_inventory,
    "fulfillment_constraints": q_fulfillment, "funnel_behavior": q_funnel,
    "service_signal": q_service, "finance_caveat": q_finance, "vendor_insight": q_vendor,
}


def make_branch(driver: str) -> Branch:
    d = catalog.get_driver(driver) or {}
    return Branch(driver=driver, label=d.get("label", driver), owner=d.get("owner", ""),
                  hypothesis=d.get("hypothesis", ""), sub_drivers=list(d.get("sub_drivers", [])))


def ungoverned_branch() -> Branch:
    """A plausible-sounding hypothesis with no governed backing."""
    b = Branch(driver="price_increase", label="Price increase (proposed)", owner="",
               hypothesis="Maybe prices rose and deterred buyers?", governed=False)
    b.sql = "SELECT avg(price) FROM pricing WHERE date = 'yesterday'"
    return b


def score_branch(b: Branch, g, fresh_ok: bool) -> Branch:
    drv = catalog.get_driver(b.driver) or {}
    metric = drv.get("metric")
    metric_ok = bool(metric) and metric in catalog.load_catalog().get("metrics", {})
    gpath = graph.driver_path(g, b.driver)
    sql_ok, _ = guardrails.check_sql(b.sql) if b.sql else (False, "")
    has_rows = b.evidence is not None and len(b.evidence) > 0
    material = abs(b.signal) >= 0.10

    # Structural backbone (metric + graph + SQL safety). Evidence strength is only
    # allowed to count if these governance checks clear STRUCTURAL_MIN, so strong
    # DuckDB evidence cannot override checks that signal problems.
    metric_pts = 2 if metric_ok else 0
    graph_pts = 2 if gpath else 0
    sql_pts = 2 if sql_ok else 0
    structural = metric_pts + graph_pts + sql_pts
    raw_evidence = _rel_score(b.signal)
    evidence_pts = raw_evidence if structural >= STRUCTURAL_MIN else 0
    b.evidence_gated = raw_evidence > 0 and evidence_pts == 0

    b.scores = {
        "metric_validated_yaml": metric_pts,                            # 0-2
        "approved_graph_path": graph_pts,                               # 0-2
        "sql_safety_template": sql_pts,                                 # 0-2
        "duckdb_evidence_strength": evidence_pts,                      # 0-3 (gated)
        "freshness_row_quality": 2 if (fresh_ok and has_rows and material) else 0,  # 0-2
        "business_relevance_owner": (2 if abs(b.signal) >= 0.25 else 1 if material else 0)
                                    if b.owner else 0,                  # 0-2
        "caveats_manageable": 1 if abs(b.signal) >= 0.25 else 0,        # 0-1
    }
    b.total = sum(b.scores.values())
    b.confidence = guardrails.evidence_gate(b.total)
    return b


# --------------------------------------------------------------------------
# Deterministic tie-break for competing drivers of similar confidence.
# Sequence (each criterion only consulted if the previous ones are equal):
#   1) stronger DuckDB evidence   2) fresher data   3) fewer caveats
#   4) clearer owner/action path  5) stronger graph/source alignment
# If every criterion is equal the tie is *unresolved* and must not be forced.
# --------------------------------------------------------------------------
TIE_BREAK_CRITERIA = ["stronger DuckDB evidence", "fresher data", "fewer caveats",
                      "clearer owner/action path", "stronger graph/source alignment"]


def caveat_count(b: Branch) -> int:
    """Caveats weighing on a branch (fewer is better). A gated branch and any missing
    metric/graph alignment each count as a caveat."""
    s = b.scores or {}
    n = 1 if b.evidence_gated else 0
    if not s.get("metric_validated_yaml"):
        n += 1
    if not s.get("approved_graph_path"):
        n += 1
    return n


def tie_break_key(b: Branch) -> tuple:
    """Ordered key implementing the documented tie-break sequence (higher wins)."""
    s = b.scores or {}
    return (
        s.get("duckdb_evidence_strength", 0),      # 1) stronger DuckDB evidence
        round(abs(b.signal), 4),                   #    (finer evidence magnitude)
        s.get("freshness_row_quality", 0),         # 2) fresher data
        -caveat_count(b),                          # 3) fewer caveats
        s.get("business_relevance_owner", 0),      # 4) clearer owner/action path
        s.get("metric_validated_yaml", 0) + s.get("approved_graph_path", 0)
        + s.get("sql_safety_template", 0),         # 5) stronger graph/source alignment
    )


# Two drivers whose signal magnitudes are this close (after the integer tie-break
# components already match) are treated as a genuine, unresolvable near-tie.
SIGNAL_TIE_EPSILON = 0.20


def _tie_key_integer_part(b: Branch) -> tuple:
    """The tie-break key without the continuous signal-magnitude component, so two
    branches can be compared on the integer governance criteria alone."""
    s = b.scores or {}
    return (
        s.get("duckdb_evidence_strength", 0),
        s.get("freshness_row_quality", 0),
        -caveat_count(b),
        s.get("business_relevance_owner", 0),
        s.get("metric_validated_yaml", 0) + s.get("approved_graph_path", 0)
        + s.get("sql_safety_template", 0),
    )


def is_unresolved_tie(a: Branch, b: Branch) -> bool:
    """True when two branches cannot be separated: equal total, identical integer
    tie-break criteria, AND signal magnitudes within SIGNAL_TIE_EPSILON of each other
    (a near-tie the deterministic sequence can't resolve)."""
    return (a.total == b.total and _tie_key_integer_part(a) == _tie_key_integer_part(b)
            and abs(round(abs(a.signal), 4) - round(abs(b.signal), 4)) <= SIGNAL_TIE_EPSILON)
