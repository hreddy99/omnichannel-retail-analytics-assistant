"""
Synthetic retail data generation (Plan section 14).

Uses **Faker** for realistic dimension entities (products, brands, vendors,
campaigns) and vectorized numpy for the high-volume fact tables, all under a
single fixed seed so the DuckDB database is repeatable before demos. No PII, no
proprietary data - random surrogate identifiers only.

Produces the fact_/dim_ model from Plan section 14.2 and seeds the demo
scenarios from 14.3 (conversion drop, paid-social shift, inventory, fulfillment,
and a funnel-behavior signal). The seeded "expected outcomes" are written to a
separate evaluation-only table (`eval_expected_outcomes`) that the assistant
never reads during normal analysis (Plan sections 14, 18).
"""
from __future__ import annotations

import datetime as dt

import duckdb
import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
BASELINE_DAYS = 40            # >= 30-45 baseline days (Plan 14.1) ...
N_DAYS = BASELINE_DAYS + 1    # ... plus one seeded "yesterday"
TODAY = dt.date(2026, 6, 7)

CHANNELS = ["organic", "paid_search", "paid_social", "email", "direct"]
DEVICES = ["desktop", "mobile", "tablet"]
REGIONS = ["northeast", "southeast", "midwest", "west"]
FULFILLMENT_TYPES = ["ship_to_home", "pickup", "same_day"]
EVENT_STAGES = ["product_view", "add_to_cart", "checkout_start", "purchase"]

CATEGORIES = [  # (id, name, department, owner)
    ("C01", "Electronics", "Hardlines", "Merchandising"),
    ("C02", "Apparel", "Softlines", "Merchandising"),
    ("C03", "Home", "Hardlines", "Merchandising"),
    ("C04", "Beauty", "Health & Beauty", "Merchandising"),
    ("C05", "Toys", "Seasonal", "Merchandising"),
    ("C06", "Grocery", "Consumables", "Merchandising"),
]
CAT_IDS = [c[0] for c in CATEGORIES]

BASELINE_CONVERSION = {  # per-channel baseline conversion
    "organic": 0.046, "paid_search": 0.039, "paid_social": 0.024,
    "email": 0.061, "direct": 0.053,
}
BASE_SHARE = {  # per-channel session share
    "organic": 0.32, "paid_search": 0.24, "paid_social": 0.12,
    "email": 0.14, "direct": 0.18,
}

# Seeded scenario knobs (evaluation-only knowledge).
PAID_SOCIAL_TARGET_SHARE = 0.22        # scenario 2: traffic shift
SCEN = {
    "paid_social_conv_mult": 0.70,     # scenario 2: converts below baseline
    "inventory_category": "C01",       # scenario 3: Electronics stockout
    "inventory_conv_mult": 0.65,
    "fulfillment_region": "west",      # scenario 4: delays / fewer options
    "fulfillment_conv_mult": 0.88,
    "funnel_category": "C05",          # scenario 5: Toys cart->purchase drop
    "funnel_conv_mult": 0.85,
}


def _dates() -> list[dt.date]:
    start = TODAY - dt.timedelta(days=N_DAYS)
    return [start + dt.timedelta(days=i) for i in range(N_DAYS)]


def _build_dims(fake: Faker):
    dim_category = pd.DataFrame(
        [{"category_id": c, "category_name": n, "department": d, "owner": o}
         for c, n, d, o in CATEGORIES])

    products = []
    for i in range(60):
        cat = CAT_IDS[i % len(CAT_IDS)]
        products.append({
            "product_id": f"P{i:03d}", "product_name": fake.catch_phrase()[:40],
            "category_id": cat, "brand": fake.company(),
            "price_band": np.random.choice(["value", "mid", "premium"]),
            "price": round(float(np.random.uniform(8, 480)), 2),
            "vendor_id": f"V{np.random.randint(1, 16):02d}",
            "cpg_partner_flag": bool(np.random.random() < 0.3),
        })
    dim_product = pd.DataFrame(products)

    camp_owner = "Marketing"
    campaigns = [{"campaign_id": "none", "campaign_name": "none", "channel": "none",
                  "start_date": None, "end_date": None, "spend": 0.0,
                  "audience": "none", "owner": camp_owner}]
    for i in range(12):
        ch = np.random.choice(["paid_search", "paid_social", "email"])
        campaigns.append({
            "campaign_id": f"CMP{i:02d}", "campaign_name": fake.bs().title()[:40],
            "channel": ch, "start_date": TODAY - dt.timedelta(days=60),
            "end_date": TODAY + dt.timedelta(days=10),
            "spend": round(float(np.random.uniform(500, 9000)), 2),
            "audience": np.random.choice(["prospecting", "retargeting", "loyalty"]),
            "owner": camp_owner})
    dim_campaign = pd.DataFrame(campaigns)
    return dim_category, dim_product, dim_campaign


def generate(seed: int = SEED) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    np.random.seed(seed)
    fake = Faker()
    Faker.seed(seed)

    dates = _dates()
    target_day = dates[-1]
    dim_category, dim_product, dim_campaign = _build_dims(fake)
    paid_campaigns = {ch: dim_campaign[dim_campaign.channel == ch].campaign_id.tolist()
                      for ch in ["paid_search", "paid_social", "email"]}

    sess_frames, order_frames, item_frames, event_frames = [], [], [], []
    inv_rows, ful_rows, fin_rows, contact_rows = [], [], [], []
    order_counter = 0

    for d in dates:
        is_t = d == target_day
        n = int(rng.normal(4000, 150))

        # ---- channel assignment (scenario 2: paid_social share spikes) ----
        shares = dict(BASE_SHARE)
        if is_t:
            shares["paid_social"] = PAID_SOCIAL_TARGET_SHARE
            rest = 1 - PAID_SOCIAL_TARGET_SHARE
            others = {k: v for k, v in BASE_SHARE.items() if k != "paid_social"}
            tot = sum(others.values())
            for k in others:
                shares[k] = others[k] / tot * rest
        ch_arr = rng.choice(CHANNELS, size=n, p=[shares[c] for c in CHANNELS])
        cat_arr = rng.choice(CAT_IDS, size=n)
        reg_arr = rng.choice(REGIONS, size=n)
        dev_arr = rng.choice(DEVICES, size=n, p=[0.45, 0.42, 0.13])

        # ---- conversion probability + seeded effects ----
        p = np.array([BASELINE_CONVERSION[c] for c in ch_arr]) * rng.normal(1.0, 0.04, n)
        if is_t:
            p = np.where(ch_arr == "paid_social", p * SCEN["paid_social_conv_mult"], p)
            p = np.where(cat_arr == SCEN["inventory_category"], p * SCEN["inventory_conv_mult"], p)
            p = np.where(reg_arr == SCEN["fulfillment_region"], p * SCEN["fulfillment_conv_mult"], p)
            p = np.where(cat_arr == SCEN["funnel_category"], p * SCEN["funnel_conv_mult"], p)
        converted = rng.random(n) < np.clip(p, 0, 1)

        # campaign id per session (paid channels only)
        camp_arr = np.full(n, "none", dtype=object)
        for ch in ["paid_search", "paid_social", "email"]:
            mask = ch_arr == ch
            if mask.any() and paid_campaigns[ch]:
                camp_arr[mask] = rng.choice(paid_campaigns[ch], size=int(mask.sum()))

        base = len(sum((len(f) for f in sess_frames) for _ in [0]) if False else [])  # noqa
        sid = np.array([f"s{d.isoformat()}_{i}" for i in range(n)], dtype=object)
        sess_frames.append(pd.DataFrame({
            "session_id": sid, "date": d, "channel": ch_arr, "campaign_id": camp_arr,
            "device": dev_arr, "region": reg_arr, "category_id": cat_arr,
            "converted": converted}))

        # ---- orders (numerator) from converted sessions ----
        conv_idx = np.where(converted)[0]
        if len(conv_idx):
            oids = np.array([f"o{order_counter + j}" for j in range(len(conv_idx))], dtype=object)
            order_counter += len(conv_idx)
            ftype = rng.choice(FULFILLMENT_TYPES, size=len(conv_idx), p=[0.6, 0.25, 0.15])
            gross = np.round(rng.uniform(15, 420, len(conv_idx)), 2)
            order_frames.append(pd.DataFrame({
                "order_id": oids, "session_id": sid[conv_idx], "date": d,
                "channel": ch_arr[conv_idx], "region": reg_arr[conv_idx],
                "category_id": cat_arr[conv_idx], "order_status": "completed",
                "fulfillment_type": ftype, "gross_amount": gross,
                "returned": rng.random(len(conv_idx)) < 0.06}))
            # order items (1-3 per order)
            nit = rng.integers(1, 4, len(conv_idx))
            it_order, it_cat, it_qty, it_amt = [], [], [], []
            for k, c in enumerate(conv_idx):
                for _ in range(int(nit[k])):
                    it_order.append(oids[k]); it_cat.append(cat_arr[c])
                    it_qty.append(int(rng.integers(1, 3)))
                    it_amt.append(round(float(rng.uniform(8, 200)), 2))
            item_frames.append(pd.DataFrame({
                "order_item_id": [f"oi{order_counter}_{j}" for j in range(len(it_order))],
                "order_id": it_order, "product_id": rng.choice(dim_product.product_id, len(it_order)),
                "category_id": it_cat, "quantity": it_qty, "item_amount": it_amt}))

        # ---- funnel events (scenario 5 reflected via converted toys drop) ----
        # product_view: all; add_to_cart: ~35% (+ all converted); checkout_start:
        # ~half of cart (+ all converted); purchase: iff converted.
        add_cart = (rng.random(n) < 0.35) | converted
        checkout = (add_cart & (rng.random(n) < 0.55)) | converted
        ev_sid, ev_stage, ev_cat, ev_dev = [], [], [], []
        for stage, mask in [("product_view", np.ones(n, bool)), ("add_to_cart", add_cart),
                            ("checkout_start", checkout), ("purchase", converted)]:
            idx = np.where(mask)[0]
            ev_sid.extend(sid[idx]); ev_stage.extend([stage] * len(idx))
            ev_cat.extend(cat_arr[idx]); ev_dev.extend(dev_arr[idx])
        event_frames.append(pd.DataFrame({
            "event_id": [f"e{d.isoformat()}_{i}" for i in range(len(ev_sid))],
            "session_id": ev_sid, "date": d, "event_type": ev_stage,
            "category_id": ev_cat, "device": ev_dev}))

        # ---- inventory_daily (scenario 3) ----
        for cid in CAT_IDS:
            views = int(rng.normal(5200, 280))
            stockout = float(rng.uniform(0.02, 0.06))
            if is_t and cid == SCEN["inventory_category"]:
                views = int(views * 1.4); stockout = float(rng.uniform(0.34, 0.44))
            inv_rows.append({"date": d, "category_id": cid, "product_views": views,
                             "available_online_flag": round(1 - stockout, 3),
                             "stockout_rate": round(stockout, 3)})

        # ---- fulfillment (scenario 4) ----
        for reg in REGIONS:
            for ft in FULFILLMENT_TYPES:
                promise = float(rng.uniform(2.0, 3.0))
                actual = promise + float(rng.uniform(0.2, 1.2))
                options = int(rng.integers(4, 6)); cancels = int(rng.normal(12, 4))
                if is_t and reg == SCEN["fulfillment_region"]:
                    actual = promise + float(rng.uniform(3.5, 5.0))
                    options = int(rng.integers(1, 3)); cancels = int(rng.normal(40, 6))
                ful_rows.append({"date": d, "region": reg, "fulfillment_type": ft,
                                 "promise_days": round(promise, 2), "actual_days": round(actual, 2),
                                 "delay_days": round(actual - promise, 2),
                                 "options_available": options, "cancellations": max(cancels, 0)})

        # ---- finance_daily (light) ----
        for cid in CAT_IDS:
            gross = float(rng.uniform(8000, 24000))
            returns = gross * float(rng.uniform(0.04, 0.10))
            tax = gross * 0.07; shipping = gross * 0.03
            adj = gross * float(rng.uniform(-0.01, 0.01))
            fin_rows.append({"date": d, "channel": "all", "category_id": cid,
                             "gross_sales": round(gross, 2), "returns": round(returns, 2),
                             "tax": round(tax, 2), "shipping": round(shipping, 2),
                             "adjustments": round(adj, 2),
                             "net_revenue": round(gross - returns + tax + shipping + adj, 2)})

        # ---- customer contacts (light; small spike on target/west) ----
        base_contacts = int(rng.normal(60, 10))
        if is_t:
            base_contacts = int(base_contacts * 1.5)
        for _ in range(max(base_contacts, 0)):
            reason = rng.choice(["delivery_delay", "cancellation", "product_issue", "billing", "other"],
                                p=[0.3, 0.2, 0.2, 0.1, 0.2])
            contact_rows.append({"contact_id": f"c{len(contact_rows)}", "date": d,
                                 "reason_code": str(reason),
                                 "channel": str(rng.choice(["phone", "chat", "email"])),
                                 "region": str(rng.choice(REGIONS))})

    frames = {
        "fact_sessions": pd.concat(sess_frames, ignore_index=True),
        "fact_orders": pd.concat(order_frames, ignore_index=True) if order_frames else pd.DataFrame(),
        "fact_order_items": pd.concat(item_frames, ignore_index=True) if item_frames else pd.DataFrame(),
        "fact_events": pd.concat(event_frames, ignore_index=True),
        "fact_inventory_daily": pd.DataFrame(inv_rows),
        "fact_fulfillment": pd.DataFrame(ful_rows),
        "fact_finance_daily": pd.DataFrame(fin_rows),
        "fact_customer_contacts": pd.DataFrame(contact_rows),
        "dim_category": dim_category, "dim_product": dim_product, "dim_campaign": dim_campaign,
    }
    frames["eval_expected_outcomes"] = _expected_outcomes(target_day)
    frames["_meta"] = pd.DataFrame([{
        "target_day": target_day, "baseline_start": dates[-8], "baseline_end": dates[-2],
        "n_baseline_days": BASELINE_DAYS}])
    return frames


def _expected_outcomes(target_day) -> pd.DataFrame:
    """Evaluation-only seeded outcomes - NOT read during normal analysis."""
    return pd.DataFrame([
        {"scenario": "digital_conversion_drop", "owner": "Digital Analytics",
         "expected": "yesterday conversion 15-25% below prior 7-day average"},
        {"scenario": "paid_social_shift", "owner": "Marketing",
         "expected": "paid_social share up, conversion below baseline"},
        {"scenario": "inventory_availability", "owner": "Merchandising",
         "expected": f"category {SCEN['inventory_category']} high views, high stockout"},
        {"scenario": "fulfillment_constraint", "owner": "Fulfillment Operations",
         "expected": f"region {SCEN['fulfillment_region']} higher delay, fewer options"},
        {"scenario": "funnel_behavior", "owner": "Digital Analytics",
         "expected": f"category {SCEN['funnel_category']} cart-to-purchase drop"},
    ])


# Tables the assistant is allowed to query (everything except the answer key).
EVAL_ONLY_TABLES = {"eval_expected_outcomes"}


def build_duckdb(seed: int = SEED, include_eval: bool = False) -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with all synthetic tables. The evaluation-only answer key
    is excluded from the analysis connection unless include_eval=True (tests)."""
    frames = generate(seed)
    con = duckdb.connect(":memory:")
    for name, df in frames.items():
        if name.startswith("_"):
            continue
        if name in EVAL_ONLY_TABLES and not include_eval:
            continue
        con.register(f"_t_{name}", df)
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM _t_{name}")
        con.unregister(f"_t_{name}")
    return con


def get_meta(seed: int = SEED) -> dict:
    m = generate(seed)["_meta"].iloc[0]
    return {"target_day": str(m["target_day"]), "baseline_start": str(m["baseline_start"]),
            "baseline_end": str(m["baseline_end"]), "n_baseline_days": int(m["n_baseline_days"])}


if __name__ == "__main__":
    f = generate()
    for k, v in f.items():
        if not k.startswith("_"):
            print(f"{k:24s} {len(v):>8,} rows")
