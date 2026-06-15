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
RAMP_DAYS = 10                # gentle operational-degradation window before "yesterday"
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
    "paid_social_conv_mult": 0.78,     # scenario 2: converts below baseline
    "inventory_category": "C01",       # scenario 3: Electronics stockout
    "inventory_conv_mult": 0.78,
    "fulfillment_region": "west",      # scenario 4: delays / fewer options
    "fulfillment_conv_mult": 0.88,
    "funnel_category": "C05",          # scenario 5: Toys cart->purchase drop
    "funnel_conv_mult": 0.90,
    "vendor_id": "V04",                # Phase III: seeded high-impact CPG partner
    "vendor_category": "C01",          # ... in Electronics
    "margin_weak_category": "C04",     # Phase III: weak margin-proxy category (Beauty)
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
        vendor = f"V{np.random.randint(1, 16):02d}"
        # Pin the seeded CPG partner (V04) onto the Electronics category (C01) so the
        # vendor scorecard and dim_product agree on who owns the seeded stockout.
        if cat == SCEN["vendor_category"] and i < len(CAT_IDS):
            vendor = SCEN["vendor_id"]
        products.append({
            "product_id": f"P{i:03d}", "product_name": fake.catch_phrase()[:40],
            "category_id": cat, "brand": fake.company(),
            "price_band": np.random.choice(["value", "mid", "premium"]),
            "price": round(float(np.random.uniform(8, 480)), 2),
            "vendor_id": vendor,
            "cpg_partner_flag": bool(vendor == SCEN["vendor_id"] or np.random.random() < 0.3),
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

    # Phase III: one governed vendor row per vendor_id used in dim_product. V04 is the
    # seeded high-impact CPG partner for Electronics (category C01).
    vendor_ids = sorted(dim_product.vendor_id.unique().tolist())
    vend_rows = []
    for vid in vendor_ids:
        is_partner = vid == SCEN["vendor_id"]
        vend_rows.append({
            "vendor_id": vid, "vendor_name": fake.company()[:40],
            "cpg_partner_flag": bool(is_partner or np.random.random() < 0.25),
            "category_owner": "Merchandising",
            "contact_group": "Vendor Partner Management"})
    dim_vendor = pd.DataFrame(vend_rows)

    # Phase II: contact-reason dimension. Reason codes must cover those
    # fact_customer_contacts uses; map each to a governed driver.
    reason_map = [
        ("delivery_delay", "fulfillment", "fulfillment_constraints", True),
        ("cancellation", "fulfillment", "fulfillment_constraints", True),
        ("product_issue", "merchandising", "inventory_availability", False),
        ("billing", "finance", "finance_caveat", False),
        ("other", "general", "service_signal", False),
    ]
    dim_contact_reason = pd.DataFrame(
        [{"reason_code": rc, "reason_group": rg, "related_driver": rd,
          "escalation_flag": esc} for rc, rg, rd, esc in reason_map])

    # Phase II: one row per region with zone / carrier / owner attributes.
    dim_region = pd.DataFrame([{
        "region": reg, "zone_id": f"Z{i+1:02d}",
        "carrier_group": np.random.choice(["national_a", "national_b", "regional"]),
        "fulfillment_owner": "Fulfillment Operations"} for i, reg in enumerate(REGIONS)])

    return (dim_category, dim_product, dim_campaign, dim_vendor,
            dim_contact_reason, dim_region)


def generate(seed: int = SEED) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    np.random.seed(seed)
    fake = Faker()
    Faker.seed(seed)

    dates = _dates()
    target_day = dates[-1]
    (dim_category, dim_product, dim_campaign, dim_vendor,
     dim_contact_reason, dim_region) = _build_dims(fake)
    paid_campaigns = {ch: dim_campaign[dim_campaign.channel == ch].campaign_id.tolist()
                      for ch in ["paid_search", "paid_social", "email"]}

    sess_frames, order_frames, item_frames, event_frames = [], [], [], []
    inv_rows, ful_rows, fin_rows, contact_rows = [], [], [], []
    return_rows, camp_rows, vendor_rows, margin_rows = [], [], [], []
    order_counter = 0

    # Phase III: map each category to the vendors that supply it, so the daily
    # vendor scorecard is consistent with dim_product's vendor->category wiring.
    cat_vendors = {cid: sorted(dim_product[dim_product.category_id == cid].vendor_id.unique().tolist())
                   for cid in CAT_IDS}

    for d in dates:
        is_t = d == target_day
        n = int(rng.normal(4000, 150))
        # Gentle degradation ramp over the last RAMP_DAYS (0 early, ~1 by yesterday)
        # for operational metrics, so trend/anomaly/risk themes have real signal.
        days_to_t = (target_day - d).days
        ramp = max(0.0, (RAMP_DAYS - days_to_t) / RAMP_DAYS) if days_to_t <= RAMP_DAYS else 0.0

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

        sid = np.array([f"s{d.isoformat()}_{i}" for i in range(n)], dtype=object)
        sess_frames.append(pd.DataFrame({
            "session_id": sid, "date": d, "channel": ch_arr, "campaign_id": camp_arr,
            "device": dev_arr, "region": reg_arr, "category_id": cat_arr,
            "converted": converted}))

        # ---- orders (numerator) from converted sessions ----
        day_orders = None
        conv_idx = np.where(converted)[0]
        if len(conv_idx):
            oids = np.array([f"o{order_counter + j}" for j in range(len(conv_idx))], dtype=object)
            order_counter += len(conv_idx)
            ftype = rng.choice(FULFILLMENT_TYPES, size=len(conv_idx), p=[0.6, 0.25, 0.15])
            gross = np.round(rng.uniform(15, 420, len(conv_idx)), 2)
            returned = rng.random(len(conv_idx)) < 0.06
            day_orders = pd.DataFrame({
                "order_id": oids, "session_id": sid[conv_idx], "date": d,
                "channel": ch_arr[conv_idx], "region": reg_arr[conv_idx],
                "category_id": cat_arr[conv_idx], "order_status": "completed",
                "fulfillment_type": ftype, "gross_amount": gross,
                "returned": returned})
            order_frames.append(day_orders)
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

            # ---- fact_returns: the ~6% of orders flagged returned (Phase II) ----
            ret_idx = np.where(returned)[0]
            if len(ret_idx):
                reasons = rng.choice(
                    ["damaged", "wrong_item", "not_as_described", "changed_mind", "late_delivery"],
                    size=len(ret_idx), p=[0.22, 0.18, 0.20, 0.30, 0.10])
                # late_delivery returns lean toward the constrained west region on yesterday
                ret_amt = np.round(gross[ret_idx] * rng.uniform(0.4, 1.0, len(ret_idx)), 2)
                return_rows.append(pd.DataFrame({
                    "return_id": [f"r{oids[j]}" for j in ret_idx],
                    "order_id": oids[ret_idx], "product_id": rng.choice(dim_product.product_id, len(ret_idx)),
                    "category_id": cat_arr[conv_idx][ret_idx], "return_date": d,
                    "return_reason": reasons, "return_amount": ret_amt}))

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
            # affected category drifts up gently over the ramp window
            if cid == SCEN["inventory_category"]:
                stockout += 0.10 * ramp
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
                # affected region's delay/cancellations creep up over the ramp window
                if reg == SCEN["fulfillment_region"]:
                    actual += 1.5 * ramp
                    cancels += int(15 * ramp)
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
            # deterministic rate (like tax/shipping) so this does not consume a draw
            # from the shared RNG stream and perturb downstream session/conversion seeds
            discount = gross * 0.05
            tax = gross * 0.07; shipping = gross * 0.03
            adj = gross * float(rng.uniform(-0.01, 0.01))
            # Recognized net revenue excludes tax/shipping and is reduced by returns,
            # discounts, and adjustments, so net is always below gross (the gross-to-net
            # bridge). Tax/shipping are reported separately, not part of merchandise net.
            net = gross - returns - discount + adj
            # margin proxy: gross-margin-ish ratio; one category runs structurally weak
            margin = float(rng.uniform(0.34, 0.46))
            if cid == SCEN["margin_weak_category"]:
                margin = float(rng.uniform(0.12, 0.20))
            fin_rows.append({"date": d, "channel": "all", "category_id": cid,
                             "gross_sales": round(gross, 2), "returns": round(returns, 2),
                             "discounts": round(discount, 2),
                             "tax": round(tax, 2), "shipping": round(shipping, 2),
                             "adjustments": round(adj, 2),
                             "net_revenue": round(net, 2),
                             "margin_proxy": round(margin, 4)})

        # ---- customer contacts (light; rising over the ramp, spike on target) ----
        # On yesterday, delivery_delay contacts concentrate in the constrained west
        # region and link to a real west order so service<->fulfillment is traceable.
        west_delay_orders = (day_orders[day_orders.region == SCEN["fulfillment_region"]]
                             .order_id.tolist() if day_orders is not None else [])
        base_contacts = int(rng.normal(60, 10) * (1 + 0.5 * ramp))
        if is_t:
            base_contacts = int(base_contacts * 1.5)
        for _ in range(max(base_contacts, 0)):
            if is_t:  # yesterday: more delivery_delay, skewed west
                reason = rng.choice(["delivery_delay", "cancellation", "product_issue", "billing", "other"],
                                    p=[0.42, 0.20, 0.15, 0.08, 0.15])
            else:
                reason = rng.choice(["delivery_delay", "cancellation", "product_issue", "billing", "other"],
                                    p=[0.3, 0.2, 0.2, 0.1, 0.2])
            reason = str(reason)
            if reason in ("delivery_delay", "cancellation") and is_t and rng.random() < 0.7:
                region = SCEN["fulfillment_region"]
            else:
                region = str(rng.choice(REGIONS))
            # link delivery_delay/cancellation contacts to a real west order where possible
            order_id = None
            if reason in ("delivery_delay", "cancellation") and region == SCEN["fulfillment_region"] \
                    and west_delay_orders:
                order_id = str(rng.choice(west_delay_orders))
            contact_rows.append({"contact_id": f"c{len(contact_rows)}", "date": d,
                                 "reason_code": reason,
                                 "channel": str(rng.choice(["phone", "chat", "email"])),
                                 "region": region, "order_id": order_id,
                                 "resolution_status": str(rng.choice(
                                     ["resolved", "pending", "escalated"], p=[0.6, 0.3, 0.1])),
                                 "wait_time_minutes": round(float(
                                     rng.uniform(2, 15) + (8 * ramp if is_t else 0)), 1)})

        # ---- fact_campaign_daily: per campaign/day aggregate from sessions/orders ----
        sess_today = sess_frames[-1]
        for camp_id in dim_campaign.campaign_id:
            if camp_id == "none":
                continue
            cmask = sess_today.campaign_id.values == camp_id
            sessions = int(cmask.sum())
            if sessions == 0:
                continue
            ch = dim_campaign.loc[dim_campaign.campaign_id == camp_id, "channel"].iloc[0]
            c_orders = int(sess_today.converted.values[cmask].sum())
            clicks = sessions  # one session per paid click in this synthetic model
            impressions = int(clicks / float(rng.uniform(0.02, 0.05)))
            spend = round(clicks * float(rng.uniform(0.4, 1.6)), 2)
            conv_rate = c_orders / sessions if sessions else 0.0
            camp_rows.append({"campaign_id": camp_id, "date": d, "channel": ch,
                              "spend": spend, "impressions": impressions, "clicks": clicks,
                              "sessions": sessions, "orders": c_orders,
                              "conversion_rate": round(conv_rate, 4),
                              "campaign_owner": "Marketing"})

        # ---- fact_vendor_scorecard: one row per vendor/category/day (Phase III) ----
        # Built from the day's category stockout + orders/returns so the seeded CPG
        # partner (V04 in C01) shows elevated stockout_impact + lost_sales_proxy on
        # yesterday, consistent with the inventory scenario.
        stockout_by_cat = {r["category_id"]: r["stockout_rate"] for r in inv_rows if r["date"] == d}
        for cid in CAT_IDS:
            cat_gross = float(day_orders[day_orders.category_id == cid].gross_amount.sum()) \
                if day_orders is not None else 0.0
            stockout = stockout_by_cat.get(cid, 0.04)
            for vid in cat_vendors[cid]:
                seeded = vid == SCEN["vendor_id"] and cid == SCEN["vendor_category"]
                # split category demand across its vendors as a rough share
                share = 1.0 / max(len(cat_vendors[cid]), 1)
                stockout_impact = round(stockout * (1.0 + (0.5 if seeded else 0.0)), 4)
                lost_sales = round(cat_gross * share * stockout_impact, 2)
                if is_t and seeded:
                    stockout_impact = round(min(stockout * 1.4, 0.6), 4)
                    lost_sales = round(cat_gross * share * stockout_impact * 2.2, 2)
                ret_rate = round(float(rng.uniform(0.04, 0.10)) + (0.03 if seeded else 0.0), 4)
                margin = float(rng.uniform(0.30, 0.46))
                if cid == SCEN["margin_weak_category"]:
                    margin = float(rng.uniform(0.12, 0.20))
                service = int(rng.integers(0, 4) + (rng.integers(3, 8) if (is_t and seeded) else 0))
                vendor_rows.append({"date": d, "vendor_id": vid, "category_id": cid,
                                    "stockout_impact": stockout_impact,
                                    "lost_sales_proxy": lost_sales,
                                    "return_rate": ret_rate, "margin_proxy": round(margin, 4),
                                    "service_issues": service})

        # ---- fact_margin_proxy_daily: one row per category/day (Phase III) ----
        # Net sales less discount/return pressure; the weak category runs structurally
        # low margin, mirroring fact_finance_daily's margin_proxy.
        day_fin = {r["category_id"]: r for r in fin_rows if r["date"] == d}
        day_ret = {}
        if return_rows and (return_rows[-1]["return_date"].iloc[0] == d):
            day_ret = return_rows[-1].groupby("category_id").return_amount.sum().to_dict()
        for cid in CAT_IDS:
            fr = day_fin.get(cid)
            net = float(fr["net_revenue"]) if fr else float(rng.uniform(8000, 24000))
            discount = round(net * float(rng.uniform(0.03, 0.09)), 2)
            ret_amt = round(float(day_ret.get(cid, net * float(rng.uniform(0.02, 0.06)))), 2)
            margin = float(fr["margin_proxy"]) if fr else float(rng.uniform(0.30, 0.46))
            margin_rows.append({"date": d, "category_id": cid, "net_sales": round(net, 2),
                                "discount_amount": discount, "return_amount": ret_amt,
                                "margin_proxy": round(margin, 4)})

    frames = {
        "fact_sessions": pd.concat(sess_frames, ignore_index=True),
        "fact_orders": pd.concat(order_frames, ignore_index=True) if order_frames else pd.DataFrame(),
        "fact_order_items": pd.concat(item_frames, ignore_index=True) if item_frames else pd.DataFrame(),
        "fact_events": pd.concat(event_frames, ignore_index=True),
        "fact_inventory_daily": pd.DataFrame(inv_rows),
        "fact_fulfillment": pd.DataFrame(ful_rows),
        "fact_finance_daily": pd.DataFrame(fin_rows),
        "fact_customer_contacts": pd.DataFrame(contact_rows),
        "fact_returns": pd.concat(return_rows, ignore_index=True) if return_rows else pd.DataFrame(),
        "fact_campaign_daily": pd.DataFrame(camp_rows),
        "fact_vendor_scorecard": pd.DataFrame(vendor_rows),
        "fact_margin_proxy_daily": pd.DataFrame(margin_rows),
        "dim_category": dim_category, "dim_product": dim_product, "dim_campaign": dim_campaign,
        "dim_vendor": dim_vendor, "dim_contact_reason": dim_contact_reason, "dim_region": dim_region,
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
