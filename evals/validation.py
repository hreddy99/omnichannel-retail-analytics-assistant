"""
Synthetic data validation checks (Plan section 14.4).

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
        avg(CASE WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' AND channel='paid_social' THEN 1.0
                 WHEN date BETWEEN DATE '{b0}' AND DATE '{b1}' THEN 0.0 END) AS share_b,
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
