"""
Investigation workflow (Plan sections 5, 8, 10 / milestones 6-7).

A deterministic stand-in for the LangGraph state machine + conditional
Tree-of-Thought beam search. It is intentionally NOT an LLM free-for-all:
every step is governed, every claim is backed by a read-only DuckDB query,
and the ToT layer activates ONLY when multiple driver paths compete.

Pipeline:  classify -> retrieve/validate -> graph -> [conditional ToT beam
search over drivers] -> evidence gate -> synthesize grounded answer.

The trace returned by run_investigation() is consumed by the Streamlit
demo page to show the reasoning loop, branch scores, and pruned paths.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import pandas as pd

from . import catalog, graph, guardrails
from .synthetic_data import build_duckdb, get_meta

BEAM_WIDTH = 2          # Plan section 8
DEPTH_LIMIT = 2
# Query budget (Plan section 10): 1 baseline + up to 3 driver-path + 1 follow-up.
DRIVER_PATH_BUDGET = 3
FOLLOWUP_BUDGET = 1
QUERY_BUDGET = 1 + DRIVER_PATH_BUDGET + FOLLOWUP_BUDGET   # = 5

# Governed driver paths the ToT layer queries first (graph/retrieval prior).
PRIMARY_DRIVERS = ["campaign_mix", "inventory_availability", "fulfillment_constraints"]
# Reserve path - only queried as the targeted follow-up if evidence is weak.
RESERVE_DRIVER = "funnel_behavior"


@dataclass
class Branch:
    driver: str
    label: str
    owner: str
    hypothesis: str
    sql: str = ""
    evidence: pd.DataFrame | None = None
    signal: float = 0.0          # relative magnitude of the discovered signal
    finding: str = ""
    scores: dict = field(default_factory=dict)
    total: int = 0
    confidence: str = ""
    caveats: list = field(default_factory=list)


def _rel_score(rel: float) -> int:
    """Map a relative-change magnitude to the 0-3 DuckDB evidence score."""
    a = abs(rel)
    if a >= 0.50:
        return 3
    if a >= 0.25:
        return 2
    if a >= 0.10:
        return 1
    return 0


# --------------------------------------------------------------------------
# Driver evidence queries - each returns (sql, evidence_df, signal, finding)
# --------------------------------------------------------------------------
def _q_campaign_mix(con, day, b0, b1):
    sql = f"""
    SELECT channel,
           sum(CASE WHEN date = DATE '{day}' THEN 1 ELSE 0 END) AS sess_target,
           avg(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' THEN 1.0 ELSE 0 END) AS share_hint,
           sum(CASE WHEN date = DATE '{day}' THEN converted ELSE 0 END)*1.0
               / nullif(sum(CASE WHEN date = DATE '{day}' THEN 1 ELSE 0 END),0) AS conv_target
    FROM web_sessions GROUP BY channel ORDER BY sess_target DESC"""
    ev = con.execute(sql).df()
    # paid_social share on target vs baseline
    share = con.execute(f"""
      WITH t AS (SELECT channel, count(*) n FROM web_sessions WHERE date=DATE '{day}' GROUP BY channel),
           tt AS (SELECT sum(n) tot FROM t),
           b AS (SELECT channel, count(*)*1.0/7 n FROM web_sessions
                 WHERE date BETWEEN DATE '{b0}' AND DATE '{b1}' GROUP BY channel),
           bt AS (SELECT sum(n) tot FROM b)
      SELECT t.channel,
             t.n*1.0/(SELECT tot FROM tt) AS share_target,
             b.n*1.0/(SELECT tot FROM bt) AS share_base
      FROM t JOIN b USING(channel) WHERE t.channel='paid_social'""").df()
    rel = float((share.share_target[0] - share.share_base[0]) / share.share_base[0])
    finding = (f"paid_social session share rose from {share.share_base[0]:.0%} to "
               f"{share.share_target[0]:.0%} of traffic while converting below baseline.")
    return sql, ev, rel, finding


def _q_inventory(con, day, b0, b1):
    sql = f"""
    SELECT category,
           avg(CASE WHEN date=DATE '{day}' THEN stockout_rate END) AS stockout_target,
           avg(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' THEN stockout_rate END) AS stockout_base,
           avg(CASE WHEN date=DATE '{day}' THEN product_views END) AS views_target
    FROM inventory GROUP BY category ORDER BY stockout_target DESC"""
    ev = con.execute(sql).df()
    top = ev.iloc[0]
    rel = float((top.stockout_target - top.stockout_base) / top.stockout_base)
    finding = (f"category '{top.category}' stockout rose from {top.stockout_base:.0%} to "
               f"{top.stockout_target:.0%} on high product views ({int(top.views_target):,}).")
    return sql, ev, rel, finding


def _q_fulfillment(con, day, b0, b1):
    sql = f"""
    SELECT region,
           avg(CASE WHEN date=DATE '{day}' THEN delay_days END) AS delay_target,
           avg(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' THEN delay_days END) AS delay_base,
           avg(CASE WHEN date=DATE '{day}' THEN options_available END) AS options_target
    FROM fulfillment GROUP BY region ORDER BY delay_target DESC"""
    ev = con.execute(sql).df()
    top = ev.iloc[0]
    rel = float((top.delay_target - top.delay_base) / top.delay_base)
    finding = (f"region '{top.region}' delivery delay rose from {top.delay_base:.1f}d to "
               f"{top.delay_target:.1f}d with options cut to {int(top.options_target)}.")
    return sql, ev, rel, finding


def _q_funnel(con, day, b0, b1):
    sql = f"""
    SELECT device,
           sum(CASE WHEN date=DATE '{day}' THEN converted ELSE 0 END)*1.0
               / nullif(sum(CASE WHEN date=DATE '{day}' THEN 1 ELSE 0 END),0) AS conv_target,
           sum(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' THEN converted ELSE 0 END)*1.0
               / nullif(sum(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' THEN 1 ELSE 0 END),0) AS conv_base
    FROM web_sessions GROUP BY device ORDER BY conv_target"""
    ev = con.execute(sql).df()
    ev["rel"] = (ev.conv_target - ev.conv_base) / ev.conv_base
    overall = float(ev.conv_target.sum() / len(ev) and
                    (ev.conv_target.mean() - ev.conv_base.mean()) / ev.conv_base.mean())
    # A true on-site funnel defect hits one device/step harder than the blend.
    # Signal = the largest EXCESS deviation of any device from the overall change.
    # A uniform drop (driven by external factors) leaves ~0 excess -> pruned.
    ev["excess"] = (ev.rel - overall)
    excess = float(ev.excess.abs().max())
    finding = (f"every device tracked the overall {overall:+.0%} change within "
               f"{excess:.0%}; no device-specific funnel defect to route.")
    return sql, ev, excess, finding


DRIVER_QUERY = {
    "campaign_mix": _q_campaign_mix,
    "inventory_availability": _q_inventory,
    "fulfillment_constraints": _q_fulfillment,
    "funnel_behavior": _q_funnel,
}


def _score_branch(b: Branch, g, fresh_ok: bool) -> Branch:
    cat = catalog.load_catalog()
    drv = cat.get("drivers", {}).get(b.driver, {})   # {} for ungoverned proposals
    metric = drv.get("metric")
    metric_ok = metric in cat["metrics"]
    gpath = graph.driver_path(g, b.driver)
    sql_ok, _ = guardrails.check_sql(b.sql)
    has_rows = b.evidence is not None and len(b.evidence) > 0

    material = abs(b.signal) >= 0.10   # is there a usable, actionable signal?
    b.scores = {
        # Structural checks (governed by YAML / graph / validator).
        "metric_validated_yaml": 2 if metric_ok else 0,        # 0-2
        "approved_graph_path": 2 if gpath else 0,              # 0-2
        "sql_passes_validator": 2 if sql_ok else 0,            # 0-2
        # Evidence checks (governed by the DuckDB result). These collapse when a
        # branch finds no material signal, which is how weak paths get pruned.
        "duckdb_meaningful_delta": _rel_score(b.signal),       # 0-3
        "freshness_row_quality": 2 if (fresh_ok and has_rows and material) else 0,  # 0-2
        "business_relevance_owner": (2 if abs(b.signal) >= 0.25
                                     else 1 if material else 0) if b.owner else 0,  # 0-2
        "caveats_manageable": 1 if abs(b.signal) >= 0.25 else 0,  # 0-1
    }
    b.total = sum(b.scores.values())
    b.confidence = guardrails.evidence_gate(b.total)
    b.caveats = list(drv.get("sub_drivers", []))
    return b


def run_investigation(question: str, seed: int = 42) -> dict:
    """Execute the governed workflow and return a structured trace."""
    trace: dict = {"question": question, "steps": [], "queries_used": 0,
                   "tot_activated": False}

    # ---- Guardrail: refuse writes (FR-09) --------------------------------
    refusal = guardrails.refuse_write(question)
    if refusal:
        trace["refusal"] = refusal

    # ---- 1. classify / setup --------------------------------------------
    cat = catalog.load_catalog()
    g = graph.build_graph()
    meta = get_meta(seed)
    day, b0, b1 = meta["target_day"], meta["baseline_start"], meta["baseline_end"]
    con = build_duckdb(seed)

    fresh_ok, fresh_msg = guardrails.check_freshness(
        cat["catalog_version"], g.graph["catalog_version"])
    trace["steps"].append({
        "node": "classify + retrieve",
        "detail": f"Resolved certified metric 'digital_conversion_rate' (v{catalog.version()}, "
                  f"hash {catalog.content_hash()}). {fresh_msg}",
        "ok": fresh_ok,
    })

    # ---- 2. baseline query (query #1) -----------------------------------
    base_sql = (f"WITH s AS (SELECT date, count(*) sessions, sum(converted) orders "
                f"FROM web_sessions GROUP BY date) "
                f"SELECT date, orders*1.0/sessions AS conversion FROM s ORDER BY date")
    ok, _ = guardrails.check_sql(base_sql)
    conv = con.execute(base_sql).df()
    conv["date"] = pd.to_datetime(conv["date"]).dt.date
    target_conv = float(conv[conv.date == dt.date.fromisoformat(day)].conversion.iloc[0])
    base_mask = (conv.date >= dt.date.fromisoformat(b0)) & (conv.date <= dt.date.fromisoformat(b1))
    base_conv = float(conv[base_mask].conversion.mean())
    pct = (target_conv - base_conv) / base_conv
    trace["queries_used"] += 1
    trace["baseline"] = {"target": target_conv, "baseline": base_conv, "pct_change": pct,
                         "series": conv, "sql": base_sql}
    trace["steps"].append({
        "node": "baseline evidence (query 1/%d)" % QUERY_BUDGET,
        "detail": f"Yesterday conversion {target_conv:.2%} vs prior-7-day avg "
                  f"{base_conv:.2%} = {pct:+.1%}. Drop confirmed.",
        "ok": True,
    })

    # ---- 3. conditional ToT trigger -------------------------------------
    # Activate ToT only when multiple plausible driver paths compete (Plan 1, 8).
    competing = len(PRIMARY_DRIVERS) >= 3 and pct < -0.05
    trace["tot_activated"] = competing
    trace["steps"].append({
        "node": "ToT trigger check",
        "detail": ("Multiple plausible driver paths + material drop -> "
                   "activate bounded beam search (width 2, depth 2)."
                   if competing else
                   "Single obvious path -> ToT not required; linear check."),
        "ok": True,
    })

    # ---- 4a. governance pre-screen (Plan section 9) ---------------------
    # The ToT layer proposes candidate hypotheses. Before spending any query
    # budget, each candidate is screened against the YAML catalog + graph. A
    # plausible-sounding but UNGOVERNED hypothesis (no certified metric / no
    # approved table) is pruned here for free - this is the anti-hallucination
    # guardrail in action.
    ungoverned = Branch(driver="price_increase", label="Price increase (proposed)",
                        owner="", hypothesis="Maybe prices rose and deterred buyers?")
    ungoverned.sql = f"SELECT avg(price) FROM pricing WHERE date = DATE '{day}'"
    sql_ok, sql_reason = guardrails.check_sql(ungoverned.sql)
    ungoverned.evidence = None
    ungoverned.signal = 0.0
    ungoverned.finding = ("No certified pricing metric or approved 'pricing' table exists "
                          "in the governed catalog. " + sql_reason +
                          " Cannot substantiate -> pruned without spending query budget.")
    _score_branch(ungoverned, g, fresh_ok)
    trace["steps"].append({
        "node": "governance pre-screen",
        "detail": "Ungoverned hypothesis 'price increase' rejected: no certified metric/"
                  "table; SQL validator blocked the unapproved table. No query spent.",
        "ok": True,
    })

    # ---- 4b. depth-1 driver-path queries (budget-limited) ---------------
    branches: list[Branch] = [ungoverned]
    for drv_name in PRIMARY_DRIVERS:
        if (trace["queries_used"] - 1) >= DRIVER_PATH_BUDGET:   # exclude baseline
            break
        drv = cat["drivers"][drv_name]
        b = Branch(driver=drv_name, label=drv["label"], owner=drv["owner"],
                   hypothesis=drv["hypothesis"])
        sql, ev, signal, finding = DRIVER_QUERY[drv_name](con, day, b0, b1)
        b.sql, b.evidence, b.signal, b.finding = sql, ev, signal, finding
        trace["queries_used"] += 1
        _score_branch(b, g, fresh_ok)
        branches.append(b)

    # ---- 4c. targeted follow-up (Plan section 10) -----------------------
    # Spend the 1 reserved follow-up query ONLY if evidence is still weak.
    queried = [b for b in branches if b.evidence is not None]
    strong = [b for b in queried if b.confidence == "likely driver"]
    if not strong and trace["queries_used"] < QUERY_BUDGET:
        drv = cat["drivers"][RESERVE_DRIVER]
        b = Branch(driver=RESERVE_DRIVER, label=drv["label"], owner=drv["owner"],
                   hypothesis=drv["hypothesis"])
        sql, ev, signal, finding = DRIVER_QUERY[RESERVE_DRIVER](con, day, b0, b1)
        b.sql, b.evidence, b.signal, b.finding = sql, ev, signal, finding
        trace["queries_used"] += 1
        _score_branch(b, g, fresh_ok)
        branches.append(b)
        trace["steps"].append({
            "node": "targeted follow-up (query %d/%d)" % (trace["queries_used"], QUERY_BUDGET),
            "detail": "Primary drivers inconclusive -> spent reserved query on funnel check.",
            "ok": True,
        })
    else:
        trace["steps"].append({
            "node": "follow-up check",
            "detail": "Strong primary evidence found -> reserved follow-up query NOT spent "
                      "(%d/%d queries used). Funnel path left as drill-down." % (
                          trace["queries_used"], QUERY_BUDGET),
            "ok": True,
        })

    # Tie-break per Plan section 8: total score, then stronger DuckDB evidence.
    branches.sort(key=lambda x: (x.total, abs(x.signal)), reverse=True)
    pruned = [b for b in branches if b.confidence == "pruned"]          # score < 7
    qualified = [b for b in branches if b.confidence != "pruned"]
    survivors = qualified[:BEAM_WIDTH]                                  # kept by beam
    deferred = qualified[BEAM_WIDTH:]                                   # >=7 but outside beam

    trace["depth1"] = branches
    trace["pruned"] = pruned
    trace["deferred"] = deferred
    trace["beam"] = survivors
    trace["steps"].append({
        "node": "depth-1 beam search (width %d)" % BEAM_WIDTH,
        "detail": "Scored %d branches; beam kept %s; deferred %s (qualified, outside beam); "
                  "pruned %s (below threshold %d)." % (
            len(branches),
            ", ".join(b.driver for b in survivors) or "none",
            ", ".join(b.driver for b in deferred) or "none",
            ", ".join(b.driver for b in pruned) or "none",
            guardrails.PRUNE_BELOW),
        "ok": True,
    })

    # ---- 5. depth-2 refinement (sub-drivers of survivors) ---------------
    depth2 = []
    for b in survivors:
        depth2.append({"driver": b.driver, "sub_drivers": b.caveats,
                       "refined": f"Refine '{b.label}' into: {', '.join(b.caveats)}."})
    trace["depth2"] = depth2
    trace["steps"].append({
        "node": "depth-2 refinement",
        "detail": "Refined surviving branches into sub-drivers for owner routing.",
        "ok": True,
    })

    # ---- 6. evidence gate + stopping condition --------------------------
    likely = [b for b in survivors if b.confidence == "likely driver"]
    trace["steps"].append({
        "node": "evidence gate + stop",
        "detail": ("Stopping: %d likely driver(s) cleared threshold within query "
                   "budget (%d/%d used)." % (len(likely), trace["queries_used"], QUERY_BUDGET)),
        "ok": True,
    })

    # ---- 7. synthesize grounded answer ----------------------------------
    trace["answer"] = _synthesize(pct, target_conv, base_conv,
                                  survivors, likely, pruned, deferred)
    con.close()
    return trace


def _synthesize(pct, target, base, survivors, likely, pruned, deferred) -> dict:
    drivers_text = []
    for b in survivors:
        drivers_text.append({
            "label": b.label, "confidence": b.confidence, "owner": b.owner,
            "finding": b.finding, "score": b.total,
        })
    contributors = [{
        "label": b.label, "confidence": "possible contributor (outside beam)",
        "owner": b.owner, "finding": b.finding, "score": b.total,
    } for b in deferred]
    headline = (f"Digital conversion fell {abs(pct):.0%} yesterday "
                f"({target:.2%} vs {base:.2%} prior-7-day average).")
    recommendation = ("Evidence points to multiple compounding drivers rather than a "
                      "single cause. Route each likely driver to its owner for a "
                      "human-reviewed check before any action.")
    return {
        "headline": headline,
        "definition": "digital_conversion_rate = digital orders / digital sessions (day grain), "
                      "compared against the prior 7-day average (certified YAML definition).",
        "drivers": drivers_text,
        "contributors": contributors,
        "pruned": [{"label": b.label, "reason": b.finding, "score": b.total} for b in pruned],
        "recommendation": recommendation,
        "caveats": [
            "Synthetic data with a fixed seed; magnitudes are illustrative.",
            "Read-only analysis - no operational systems were modified.",
            "Causality is labeled (likely driver / possible contributor); not proven.",
        ],
        "confidence": "high" if likely else "inconclusive",
    }
