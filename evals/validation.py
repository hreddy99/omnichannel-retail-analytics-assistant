"""
Synthetic data validation checks.

Confirms the generated data contains the expected demo signals and that the
evaluation-only answer key is not exposed to the analysis connection. Run:

    python -m evals.validation
"""
from __future__ import annotations

import datetime as dt

from skills import sql_skill as guardrails
from data.generator import SCEN, build_duckdb, get_meta


def run_checks(seed: int = 42) -> list[dict]:
    con = build_duckdb(seed)
    m = get_meta(seed)
    td, b0, b1 = m["target_day"], m["baseline_start"], m["baseline_end"]
    results: list[dict] = []

    def check(name, ok, detail):
        results.append({"check": name, "ok": bool(ok), "detail": detail})

    # Row counts by table
    tables = ["fact_sessions", "fact_orders", "fact_events", "fact_inventory_daily",
              "fact_fulfillment", "dim_product", "dim_category", "dim_campaign"]
    counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables}
    check("Row counts by table", all(v > 0 for v in counts.values()), str(counts))

    # Row-count coverage for the Phase II/III tables (all non-empty)
    new_tables = ["fact_returns", "fact_campaign_daily", "fact_vendor_scorecard",
                  "fact_margin_proxy_daily", "dim_vendor", "dim_contact_reason", "dim_region"]
    new_counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in new_tables}
    check("Row counts for Phase II/III tables", all(v > 0 for v in new_counts.values()),
          str(new_counts))

    # Date coverage >= 30 days
    ndays = con.execute("SELECT count(distinct date) FROM fact_sessions").fetchone()[0]
    check("Date coverage >= 30 baseline days + yesterday", ndays >= 31, f"{ndays} distinct days")

    # Baseline stability (coefficient of variation reasonable)
    base = con.execute(f"""WITH s AS (SELECT date, count(*) n, sum(CASE WHEN converted THEN 1 ELSE 0 END) o
        FROM fact_sessions WHERE date BETWEEN DATE '{b0}' AND DATE '{b1}' GROUP BY date)
        SELECT avg(o*1.0/n) mean, stddev(o*1.0/n) sd FROM s""").df().iloc[0]
    cv = float(base["sd"] / base["mean"])
    check("Conversion baseline stable", cv < 0.25, f"CV={cv:.2f}")

    # Seeded conversion drop in 15-25%
    series = con.execute("""WITH s AS (SELECT date, count(*) n, sum(CASE WHEN converted THEN 1 ELSE 0 END) o
        FROM fact_sessions GROUP BY date) SELECT date, o*1.0/n conv FROM s ORDER BY date""").df()
    series["date"] = series.date.astype(str)
    tgt = float(series.iloc[-1].conv)
    base_mean = float(series[(series.date >= b0) & (series.date <= b1)].conv.mean())
    pct = (tgt - base_mean) / base_mean
    check("Seeded conversion drop 15-25%", 0.15 <= abs(pct) <= 0.25, f"{pct:+.1%}")

    # Paid social scenario: share up + conversion down
    ps = con.execute(f"""SELECT
        sum(CASE WHEN date=DATE '{td}' AND channel='paid_social' THEN 1 ELSE 0 END)*1.0
            / sum(CASE WHEN date=DATE '{td}' THEN 1 ELSE 0 END) AS share_t,
        sum(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' AND channel='paid_social' THEN 1 ELSE 0 END)*1.0
            / sum(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' THEN 1 ELSE 0 END) AS share_b,
        sum(CASE WHEN date=DATE '{td}' AND channel='paid_social' AND converted THEN 1 ELSE 0 END)*1.0
            / sum(CASE WHEN date=DATE '{td}' AND channel='paid_social' THEN 1 ELSE 0 END) AS conv_t
        FROM fact_sessions""").df().iloc[0]
    check("Paid social share up + conversion down", ps.share_t > ps.share_b and ps.conv_t < 0.024,
          f"share {ps.share_b:.0%}->{ps.share_t:.0%}, conv_t {ps.conv_t:.3f}")

    # Inventory scenario
    inv = con.execute(f"""SELECT stockout_rate FROM fact_inventory_daily
        WHERE date=DATE '{td}' AND category_id='{SCEN['inventory_category']}'""").fetchone()[0]
    check("Inventory stockout pressure on seeded category", inv > 0.3,
          f"{SCEN['inventory_category']} stockout {inv:.0%}")

    # Fulfillment scenario
    ful = con.execute(f"""SELECT avg(delay_days) d, avg(options_available) o FROM fact_fulfillment
        WHERE date=DATE '{td}' AND region='{SCEN['fulfillment_region']}'""").df().iloc[0]
    check("Fulfillment delay/option pressure on seeded region", ful.d > 3 and ful.o < 3,
          f"{SCEN['fulfillment_region']} delay {ful.d:.1f}d, opts {ful.o:.1f}")

    # Returns tie to orders flagged returned (Phase II)
    ret = con.execute("""SELECT
        (SELECT count(*) FROM fact_returns) AS total,
        (SELECT count(*) FROM fact_returns f JOIN fact_orders o ON f.order_id=o.order_id
            WHERE o.returned) AS tied""").df().iloc[0]
    check("Returns exist and tie to returned orders", ret.total > 0 and ret.tied == ret.total,
          f"{int(ret.tied)}/{int(ret.total)} returns map to returned orders")

    # Service: delivery-delay contacts spike on yesterday, concentrated in west
    svc = con.execute(f"""SELECT
        sum(CASE WHEN date=DATE '{td}' AND reason_code='delivery_delay' THEN 1 ELSE 0 END) AS dd_t,
        avg(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' AND reason_code='delivery_delay'
            THEN 1.0 ELSE 0.0 END) AS share_b,
        sum(CASE WHEN date=DATE '{td}' AND reason_code='delivery_delay'
            AND region='{SCEN['fulfillment_region']}' THEN 1 ELSE 0 END) AS dd_west_t
        FROM fact_customer_contacts""").df().iloc[0]
    west_frac = float(svc.dd_west_t) / float(svc.dd_t) if svc.dd_t else 0.0
    check("Service delivery-delay spike concentrated in west",
          svc.dd_t > 0 and west_frac > 0.5, f"{int(svc.dd_t)} delay contacts, {west_frac:.0%} west")

    # Marketing: the highest-session paid_social campaign on yesterday converts below the
    # paid_social baseline (session-weighted) — the seeded high-volume, low-conversion case.
    camp = con.execute(f"""WITH top AS (SELECT campaign_id, sessions, conversion_rate
            FROM fact_campaign_daily WHERE date=DATE '{td}' AND channel='paid_social'
            ORDER BY sessions DESC LIMIT 1),
        base AS (SELECT sum(orders)*1.0/sum(sessions) AS conv_b FROM fact_campaign_daily
            WHERE date BETWEEN DATE '{b0}' AND DATE '{b1}' AND channel='paid_social')
        SELECT top.campaign_id, top.sessions, top.conversion_rate, base.conv_b FROM top, base""").df().iloc[0]
    check("Campaign_daily shows low-converting paid_social campaign",
          camp.sessions > 0 and camp.conversion_rate < camp.conv_b,
          f"{camp.campaign_id} sessions {int(camp.sessions)}, conv {camp.conversion_rate:.3f} "
          f"< paid_social baseline {camp.conv_b:.3f}")

    # Vendor: seeded CPG partner shows elevated stockout impact in C01 on yesterday
    vend = con.execute(f"""WITH v AS (SELECT vendor_id, stockout_impact, lost_sales_proxy
        FROM fact_vendor_scorecard WHERE date=DATE '{td}' AND category_id='{SCEN['vendor_category']}')
        SELECT (SELECT stockout_impact FROM v WHERE vendor_id='{SCEN['vendor_id']}') AS seeded,
               (SELECT max(stockout_impact) FROM v WHERE vendor_id<>'{SCEN['vendor_id']}') AS other,
               (SELECT lost_sales_proxy FROM v WHERE vendor_id='{SCEN['vendor_id']}') AS seeded_lost,
               (SELECT max(lost_sales_proxy) FROM v WHERE vendor_id<>'{SCEN['vendor_id']}') AS other_lost
        """).df().iloc[0]
    check("Vendor scorecard shows seeded vendor elevated in C01",
          vend.seeded > vend.other and vend.seeded_lost > vend.other_lost,
          f"{SCEN['vendor_id']} impact {vend.seeded:.2f} vs {vend.other:.2f}, "
          f"lost {vend.seeded_lost:.0f} vs {vend.other_lost:.0f}")

    # Finance: one category runs a structurally weak margin proxy
    mp = con.execute("""WITH m AS (SELECT category_id, avg(margin_proxy) mp
        FROM fact_margin_proxy_daily GROUP BY category_id)
        SELECT category_id, mp FROM m ORDER BY mp LIMIT 1""").df().iloc[0]
    check("Margin proxy weak category present",
          mp.category_id == SCEN["margin_weak_category"] and mp.mp < 0.25,
          f"weakest {mp.category_id} margin_proxy {mp.mp:.2f}")

    # No hidden answer key in analysis connection
    has_eval = con.execute("""SELECT count(*) FROM information_schema.tables
        WHERE table_name='eval_expected_outcomes'""").fetchone()[0]
    check("No hidden answer key in analysis DB", has_eval == 0, "eval_expected_outcomes excluded")

    # SQL safety: a write is blocked, a SELECT passes
    ok_sel, _ = guardrails.check_sql("SELECT * FROM fact_sessions")
    ok_wr, _ = guardrails.check_sql("DROP TABLE fact_sessions")
    check("SQL safety (SELECT ok, write blocked)", ok_sel and not ok_wr, "validator enforced")

    con.close()
    return results


if __name__ == "__main__":
    rows = run_checks()
    width = max(len(r["check"]) for r in rows)
    allok = True
    for r in rows:
        allok &= r["ok"]
        print(f"[{'PASS' if r['ok'] else 'FAIL'}] {r['check']:<{width}}  {r['detail']}")
    print("\n", "ALL CHECKS PASSED" if allok else "SOME CHECKS FAILED")
