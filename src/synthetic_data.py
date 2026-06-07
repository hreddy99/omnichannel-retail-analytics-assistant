"""
Synthetic retail data generation (Plan section 11).

Fully synthetic, no PII, fixed random seed. Seeds four scenarios so the demo
investigation can *discover* them through DuckDB queries:

  1. Digital conversion drop   - yesterday conversion 15-25% below 7-day avg
  2. Paid social traffic shift - paid_social sessions spike, convert below baseline
  3. Inventory availability     - selected categories: high views, low availability
  4. Fulfillment constraint     - delivery delays / fewer options in selected regions

The "expected outcomes" are evaluation-only and are NOT exposed to the
investigation workflow - the assistant must find evidence via SQL.
"""
from __future__ import annotations

import datetime as dt

import duckdb
import numpy as np
import pandas as pd

SEED = 42
N_DAYS = 14                       # 7-day baseline window + buffer + target day
CHANNELS = ["organic", "paid_search", "paid_social", "email", "direct"]
CATEGORIES = ["apparel", "electronics", "home", "beauty", "toys"]
REGIONS = ["northeast", "southeast", "midwest", "west"]
DEVICES = ["desktop", "mobile", "tablet"]

# Seeded scenario knobs (evaluation-only knowledge).
AFFECTED_CATEGORY = "electronics"     # inventory issue
AFFECTED_REGION = "west"              # fulfillment issue
BASELINE_CONVERSION = {
    "organic": 0.045, "paid_search": 0.038, "paid_social": 0.022,
    "email": 0.060, "direct": 0.052,
}
BASELINE_SESSION_SHARE = {
    "organic": 0.32, "paid_search": 0.24, "paid_social": 0.12,
    "email": 0.14, "direct": 0.18,
}


def _dates() -> list[dt.date]:
    today = dt.date(2026, 6, 7)
    start = today - dt.timedelta(days=N_DAYS)
    # target day ("yesterday") = today - 1
    return [start + dt.timedelta(days=i) for i in range(N_DAYS)]


def generate(seed: int = SEED) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    dates = _dates()
    target_day = dates[-1]          # the anomalous "yesterday"

    sess_rows, order_rows = [], []
    inv_rows, ful_rows, camp_rows = [], [], []
    order_id = 0

    for d in dates:
        is_target = d == target_day
        total_sessions = int(rng.normal(9000, 400))

        # --- scenario 2: paid_social traffic share spikes on the target day ---
        shares = dict(BASELINE_SESSION_SHARE)
        if is_target:
            shares["paid_social"] = 0.30          # sharp increase
            # renormalize the rest proportionally
            rest = 1 - shares["paid_social"]
            others = {k: v for k, v in BASELINE_SESSION_SHARE.items() if k != "paid_social"}
            tot = sum(others.values())
            for k in others:
                shares[k] = others[k] / tot * rest

        for ch in CHANNELS:
            n = int(total_sessions * shares[ch])
            base_conv = BASELINE_CONVERSION[ch] * rng.normal(1.0, 0.03)
            if is_target and ch == "paid_social":
                base_conv *= 0.6                  # converts well below baseline
            spend = round(n * rng.uniform(0.4, 1.2), 2) if ch.startswith("paid") else 0.0
            camp = f"{ch}_camp_{rng.integers(1, 4)}" if ch.startswith("paid") else "none"
            camp_rows.append({"date": d, "channel": ch, "campaign": camp,
                              "sessions": n, "spend": spend})

            for _ in range(n):
                cat = rng.choice(CATEGORIES)
                region = rng.choice(REGIONS)
                conv_p = base_conv

                # --- scenario 3: inventory issue suppresses target-day conversion ---
                if is_target and cat == AFFECTED_CATEGORY:
                    conv_p *= 0.45
                # --- scenario 4: fulfillment issue suppresses target-day conversion ---
                if is_target and region == AFFECTED_REGION:
                    conv_p *= 0.7

                converted = int(rng.random() < conv_p)
                sess_rows.append({
                    "session_id": f"s{len(sess_rows)}", "date": d, "channel": ch,
                    "campaign": camp, "category": cat, "region": region,
                    "device": rng.choice(DEVICES), "converted": converted,
                })
                if converted:
                    order_id += 1
                    order_rows.append({
                        "order_id": f"o{order_id}", "date": d, "channel": ch,
                        "region": region, "category": cat,
                        "gross_amount": round(rng.uniform(20, 400), 2),
                        "returned": int(rng.random() < 0.06),
                    })

        # --- inventory table ---
        for cat in CATEGORIES:
            views = int(rng.normal(5000, 300))
            stockout = rng.uniform(0.02, 0.06)
            if is_target and cat == AFFECTED_CATEGORY:
                views = int(views * 1.4)          # high product views
                stockout = rng.uniform(0.35, 0.45)  # low availability
            inv_rows.append({
                "date": d, "category": cat, "product_views": views,
                "available_online_flag": round(1 - stockout, 3),
                "stockout_rate": round(stockout, 3),
            })

        # --- fulfillment table ---
        for region in REGIONS:
            delay = rng.uniform(1.0, 2.0)
            options = rng.integers(4, 6)
            cancels = int(rng.normal(40, 8))
            if is_target and region == AFFECTED_REGION:
                delay = rng.uniform(4.5, 6.0)     # delivery delays
                options = rng.integers(1, 3)      # reduced options
                cancels = int(rng.normal(120, 15))
            ful_rows.append({
                "date": d, "region": region, "delay_days": round(delay, 2),
                "options_available": int(options), "cancellations": cancels,
            })

    return {
        "web_sessions": pd.DataFrame(sess_rows),
        "orders": pd.DataFrame(order_rows),
        "inventory": pd.DataFrame(inv_rows),
        "fulfillment": pd.DataFrame(ful_rows),
        "campaigns": pd.DataFrame(camp_rows),
        "_meta": pd.DataFrame([{"target_day": target_day,
                                "baseline_start": dates[-8],
                                "baseline_end": dates[-2]}]),
    }


def build_duckdb(seed: int = SEED) -> duckdb.DuckDBPyConnection:
    """Return an in-memory read-only-by-convention DuckDB with all tables."""
    frames = generate(seed)
    con = duckdb.connect(":memory:")
    for name, df in frames.items():
        if name.startswith("_"):
            continue
        con.register(f"_tmp_{name}", df)
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM _tmp_{name}")
        con.unregister(f"_tmp_{name}")
    return con


def get_meta(seed: int = SEED) -> dict:
    m = generate(seed)["_meta"].iloc[0]
    return {"target_day": str(m["target_day"]),
            "baseline_start": str(m["baseline_start"]),
            "baseline_end": str(m["baseline_end"])}


if __name__ == "__main__":
    f = generate()
    for k, v in f.items():
        print(f"{k:14s} {len(v):>7,} rows")
