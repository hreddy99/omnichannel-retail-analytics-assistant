"""
Themed reviews, cross-functional investigations that are neither the conversion-
drop investigation nor single-metric lookups. A mix of health checks, week-over-week
trend/anomaly reviews, and forward-looking risk watch-outs. Each runs 2-3 read-only
governed queries and returns a headline, signal numbers, a relevant chart spec, a
table, and an owner-routed recommendation. Several exercise the Phase II/III tables
(fact_campaign_daily, fact_margin_proxy_daily, fact_vendor_scorecard, dim_region).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Callable


@dataclass
class Theme:
    id: str
    question: str
    domain: str
    owner: str
    build: Callable     # (con, meta) -> dict


def _win(meta):
    td = dt.date.fromisoformat(meta["target_day"])
    return {"td": td.isoformat(), "l7": (td - dt.timedelta(days=6)).isoformat(),
            "l14": (td - dt.timedelta(days=13)).isoformat(),
            "p7s": (td - dt.timedelta(days=13)).isoformat(),
            "p7e": (td - dt.timedelta(days=7)).isoformat()}


def _q(con, sql):
    return con.execute(sql).df()


# ---- Health checks -------------------------------------------------------
def _exec_briefing(con, meta):
    w = _win(meta)
    conv = _q(con, f"WITH s AS (SELECT date, count(*) n, sum(CASE WHEN converted THEN 1 ELSE 0 END) o "
              f"FROM fact_sessions GROUP BY date) SELECT date, round(o*100.0/n,2) conv_pct FROM s "
              f"WHERE date BETWEEN DATE '{w['l14']}' AND DATE '{w['td']}' ORDER BY date")
    fin = _q(con, f"SELECT round(sum(net_revenue),0) net, round(sum(gross_sales),0) gross, "
             f"round(sum(returns),0) ret FROM fact_finance_daily WHERE date=DATE '{w['td']}'")
    con_t = _q(con, f"SELECT count(*) c FROM fact_customer_contacts WHERE date=DATE '{w['td']}'")
    ful = _q(con, f"SELECT f.region, g.carrier_group, round(avg(f.delay_days),2) d FROM fact_fulfillment f "
             f"JOIN dim_region g USING(region) WHERE f.date=DATE '{w['td']}' "
             f"GROUP BY f.region, g.carrier_group ORDER BY d DESC LIMIT 1")
    convy = float(conv.iloc[-1].conv_pct); f = fin.iloc[0]; fr = ful.iloc[0]
    return {"headline": f"Daily executive briefing for {w['td']}.",
            "summary": f"Conversion {convy:.2f}%; net revenue ${f.net:,.0f} (gross ${f.gross:,.0f}, "
                       f"returns ${f.ret:,.0f}); {int(con_t.iloc[0].c):,} support contacts; "
                       f"slowest region {fr.region} ({fr.carrier_group}) at {fr.d:.1f}d delay.",
            "signals": [("Conversion", f"{convy:.2f}%"), ("Net revenue", f"${f.net:,.0f}"),
                        ("Support contacts", f"{int(con_t.iloc[0].c):,}"),
                        ("Slowest region", f"{fr.region} ({fr.d:.1f}d)")],
            "chart": {"kind": "line", "x": "date", "y": "conv_pct",
                      "title": "Conversion %, last 14 days"},
            "table": conv, "recommendation": "Share with leadership; drill into the slowest region and contacts."}


def _cx_health(con, meta):
    w = _win(meta)
    daily = _q(con, f"SELECT date, count(*) contacts FROM fact_customer_contacts "
               f"WHERE date BETWEEN DATE '{w['l14']}' AND DATE '{w['td']}' GROUP BY date ORDER BY date")
    mix = _q(con, f"SELECT r.reason_group, count(*) contacts FROM fact_customer_contacts f "
             f"JOIN dim_contact_reason r USING(reason_code) "
             f"WHERE f.date BETWEEN DATE '{w['l7']}' AND DATE '{w['td']}' GROUP BY r.reason_group "
             f"ORDER BY contacts DESC")
    last7 = float(daily[daily.date.astype(str) >= w['l7']].contacts.mean())
    prior = float(daily[daily.date.astype(str) < w['l7']].contacts.mean()) or 1.0
    chg = (last7 - prior) / prior
    top = mix.iloc[0]
    return {"headline": f"Customer-experience health: contacts {'up' if chg>=0 else 'down'} "
                        f"{abs(chg):.0%} week-over-week.",
            "summary": f"Contacts averaged {last7:.0f}/day last 7 days vs {prior:.0f}/day before "
                       f"({chg:+.0%}). Top reason group: {top.reason_group} ({int(top.contacts):,}).",
            "signals": [("Contacts/day (7d)", f"{last7:.0f}"), ("WoW change", f"{chg:+.0%}"),
                        ("Top reason group", str(top.reason_group))],
            "chart": {"kind": "line", "x": "date", "y": "contacts",
                      "title": "Customer contacts per day, last 14 days"},
            "table": daily, "recommendation": "Customer Service: staff to the rising reason group; link to fulfillment."}


def _fulfillment_review(con, meta):
    w = _win(meta)
    byreg = _q(con, f"SELECT f.region, g.carrier_group, round(avg(f.delay_days),2) avg_delay_days, "
               f"round(avg(f.options_available),1) avg_options, sum(f.cancellations) cancellations "
               f"FROM fact_fulfillment f JOIN dim_region g USING(region) "
               f"WHERE f.date BETWEEN DATE '{w['l14']}' AND DATE '{w['td']}' "
               f"GROUP BY f.region, g.carrier_group ORDER BY avg_delay_days DESC")
    t = byreg.iloc[0]
    return {"headline": f"Fulfillment review (2 weeks): {t.region} slowest at {t.avg_delay_days:.2f}d "
                        f"({t.carrier_group}).",
            "summary": f"{t.region} (carrier {t.carrier_group}) averages {t.avg_delay_days:.2f}d delay "
                       f"with {t.avg_options:.1f} options and {int(t.cancellations):,} cancellations "
                       f"over the last 2 weeks.",
            "signals": [("Slowest region", str(t.region)), ("Avg delay", f"{t.avg_delay_days:.2f}d"),
                        ("Cancellations", f"{int(t.cancellations):,}")],
            "chart": {"kind": "bar", "x": "region", "y": "avg_delay_days",
                      "title": "Avg delivery delay (days) by region, last 14 days"},
            "table": byreg, "recommendation": "Fulfillment Operations: add capacity/options in the slowest region."}


def _marketing_efficiency(con, meta):
    bych = _q(con, "SELECT channel, round(sum(spend),0) spend, sum(sessions)::BIGINT sessions, "
              "sum(orders)::BIGINT orders, "
              "round(sum(orders)*100.0/nullif(sum(sessions),0),2) conv_pct, "
              "round(sum(spend)/nullif(sum(orders),0),2) cost_per_order "
              "FROM fact_campaign_daily GROUP BY channel ORDER BY conv_pct DESC")
    best, worst = bych.iloc[0], bych.iloc[-1]
    tot_spend = float(bych.spend.sum()); tot_orders = int(bych.orders.sum())
    return {"headline": f"Marketing efficiency: {best.channel} best at {best.conv_pct:.2f}% "
                        f"(${best.cost_per_order:,.2f}/order); {worst.channel} weakest "
                        f"({worst.conv_pct:.2f}%).",
            "summary": f"Across campaigns, ${tot_spend:,.0f} spend drove {int(bych.sessions.sum()):,} "
                       f"sessions and {tot_orders:,} orders. {best.channel} converts best at "
                       f"{best.conv_pct:.2f}% (${best.cost_per_order:,.2f} per order); "
                       f"{worst.channel} is weakest at {worst.conv_pct:.2f}%.",
            "signals": [("Best channel", f"{best.channel} {best.conv_pct:.2f}%"),
                        ("Best cost/order", f"${best.cost_per_order:,.2f}"),
                        ("Weakest", f"{worst.channel} {worst.conv_pct:.2f}%")],
            "chart": {"kind": "grouped", "x": "channel",
                      "series": [("sessions", "sessions", "#94a3b8"), ("orders", "orders", "#2563eb")],
                      "title": "Sessions vs orders by channel (campaigns)"},
            "table": bych, "recommendation": "Marketing: shift budget toward the lower cost-per-order channel."}


def _revenue_quality(con, meta):
    wk = _q(con, "WITH f AS (SELECT date_trunc('week', date) AS wk, round(sum(gross_sales),0) gross_sales, "
            "round(sum(net_revenue),0) net_revenue, round(sum(returns),0) AS returns_total "
            "FROM fact_finance_daily GROUP BY wk), "
            "m AS (SELECT date_trunc('week', date) AS wk, round(avg(margin_proxy)*100,1) margin_pct "
            "FROM fact_margin_proxy_daily GROUP BY wk) "
            "SELECT f.wk, f.gross_sales, f.net_revenue, f.returns_total, m.margin_pct "
            "FROM f JOIN m USING(wk) ORDER BY f.wk")
    last = wk.iloc[-1]
    ratio = last.net_revenue / last.gross_sales if last.gross_sales else 0
    return {"headline": f"Revenue quality: net is {ratio:.0%} of gross with a "
                        f"{last.margin_pct:.1f}% margin proxy in the latest week.",
            "summary": f"Latest week net ${last.net_revenue:,.0f} on gross ${last.gross_sales:,.0f} "
                       f"(returns ${last.returns_total:,.0f}); blended margin proxy {last.margin_pct:.1f}%.",
            "signals": [("Net/gross", f"{ratio:.0%}"), ("Net (latest wk)", f"${last.net_revenue:,.0f}"),
                        ("Returns (latest wk)", f"${last.returns_total:,.0f}"),
                        ("Margin proxy", f"{last.margin_pct:.1f}%")],
            "chart": {"kind": "grouped", "x": "wk",
                      "series": [("gross", "gross_sales", "#2563eb"), ("net", "net_revenue", "#16a34a")],
                      "title": "Gross vs net revenue by week"},
            "table": wk, "recommendation": "Finance: reconcile gross-to-net; watch returns and the margin proxy."}


# ---- Trend / anomaly -----------------------------------------------------
def _wow(con, meta, sql_last, sql_prior, label):
    last = float(_q(con, sql_last).iloc[0, 0] or 0)
    prior = float(_q(con, sql_prior).iloc[0, 0] or 0)
    chg = (last - prior) / prior if prior else 0
    return {"metric": label, "prior_7d": round(prior, 2), "last_7d": round(last, 2),
            "change_pct": round(chg * 100, 1)}


def _trending_worse(con, meta):
    w = _win(meta)
    import pandas as pd
    rows = [
        _wow(con, meta,
             f"SELECT avg(delay_days) FROM fact_fulfillment WHERE date BETWEEN DATE '{w['l7']}' AND DATE '{w['td']}'",
             f"SELECT avg(delay_days) FROM fact_fulfillment WHERE date BETWEEN DATE '{w['p7s']}' AND DATE '{w['p7e']}'",
             "Avg delivery delay (d)"),
        _wow(con, meta,
             f"SELECT count(*)/7.0 FROM fact_customer_contacts WHERE date BETWEEN DATE '{w['l7']}' AND DATE '{w['td']}'",
             f"SELECT count(*)/7.0 FROM fact_customer_contacts WHERE date BETWEEN DATE '{w['p7s']}' AND DATE '{w['p7e']}'",
             "Contacts/day"),
        _wow(con, meta,
             f"SELECT avg(stockout_rate)*100 FROM fact_inventory_daily WHERE date BETWEEN DATE '{w['l7']}' AND DATE '{w['td']}'",
             f"SELECT avg(stockout_rate)*100 FROM fact_inventory_daily WHERE date BETWEEN DATE '{w['p7s']}' AND DATE '{w['p7e']}'",
             "Avg stockout %"),
        _wow(con, meta,
             f"SELECT count(*) FROM fact_returns WHERE return_date BETWEEN DATE '{w['l7']}' AND DATE '{w['td']}'",
             f"SELECT count(*) FROM fact_returns WHERE return_date BETWEEN DATE '{w['p7s']}' AND DATE '{w['p7e']}'",
             "Returns (count)"),
    ]
    df = pd.DataFrame(rows).sort_values("change_pct", ascending=False)
    worst = df.iloc[0]
    return {"headline": f"Trending worse: {worst.metric} {worst.change_pct:+.1f}% week-over-week.",
            "summary": f"{worst.metric} moved from {worst.prior_7d} to {worst.last_7d} "
                       f"({worst.change_pct:+.1f}%) vs the prior week, the largest deterioration.",
            "signals": [(r.metric, f"{r.change_pct:+.1f}%") for r in df.itertuples()],
            "chart": {"kind": "bar", "x": "metric", "y": "change_pct",
                      "title": "Week-over-week change by metric (%)"},
            "table": df, "recommendation": "Route the top deteriorating metric to its owner for a check."}


def _unusual_spikes(con, meta):
    w = _win(meta)
    daily = _q(con, f"SELECT date, count(*) contacts FROM fact_customer_contacts "
               f"WHERE date BETWEEN DATE '{w['l14']}' AND DATE '{w['td']}' GROUP BY date ORDER BY date")
    mean = float(daily.contacts.mean()); sd = float(daily.contacts.std()) or 1.0
    last = float(daily.iloc[-1].contacts); z = (last - mean) / sd
    return {"headline": f"Anomaly check: yesterday's contacts are {z:.1f}σ above the 2-week mean.",
            "summary": f"Contacts yesterday {int(last):,} vs mean {mean:.0f} (±{sd:.0f}); "
                       f"{'a notable spike' if z>=2 else 'within normal range'}.",
            "signals": [("Yesterday", f"{int(last):,}"), ("2-wk mean", f"{mean:.0f}"),
                        ("Std devs", f"{z:.1f}σ")],
            "chart": {"kind": "line", "x": "date", "y": "contacts",
                      "title": "Contacts per day, last 14 days (watch for spikes)"},
            "table": daily, "recommendation": "Investigate the spike's reason codes if above 2σ."}


def _funnel_health(con, meta):
    w = _win(meta)
    daily = _q(con, f"""WITH e AS (SELECT date,
        sum(CASE WHEN event_type='add_to_cart' THEN 1 ELSE 0 END) carts,
        sum(CASE WHEN event_type='purchase' THEN 1 ELSE 0 END) purch
        FROM fact_events WHERE date BETWEEN DATE '{w['l14']}' AND DATE '{w['td']}' GROUP BY date)
        SELECT date, round(purch*100.0/nullif(carts,0),1) cart_to_purchase_pct FROM e ORDER BY date""")
    first, last = float(daily.iloc[0].cart_to_purchase_pct), float(daily.iloc[-1].cart_to_purchase_pct)
    chg = (last - first) / first if first else 0
    return {"headline": f"Funnel health: cart→purchase {last:.1f}% ({chg:+.0%} over 2 weeks).",
            "summary": f"Cart-to-purchase moved from {first:.1f}% to {last:.1f}% over the last 2 weeks.",
            "signals": [("Cart→purchase", f"{last:.1f}%"), ("2-wk change", f"{chg:+.0%}")],
            "chart": {"kind": "line", "x": "date", "y": "cart_to_purchase_pct",
                      "title": "Cart→purchase rate (%), last 14 days"},
            "table": daily, "recommendation": "Digital Analytics: audit checkout steps if the rate is falling."}


# ---- Risk ----------------------------------------------------------------
def _stockout_risk(con, meta):
    w = _win(meta)
    df = _q(con, f"""SELECT c.category_name,
        round(avg(CASE WHEN date BETWEEN DATE '{w['l7']}' AND DATE '{w['td']}' THEN stockout_rate END)*100,1) last7_pct,
        round(avg(CASE WHEN date BETWEEN DATE '{w['p7s']}' AND DATE '{w['p7e']}' THEN stockout_rate END)*100,1) prior7_pct
        FROM fact_inventory_daily i JOIN dim_category c USING(category_id)
        GROUP BY c.category_name ORDER BY last7_pct DESC""")
    df["delta_pts"] = (df.last7_pct - df.prior7_pct).round(1)
    t = df.sort_values("delta_pts", ascending=False).iloc[0]
    return {"headline": f"Stockout risk: {t.category_name} up {t.delta_pts:+.1f} pts to {t.last7_pct:.1f}%.",
            "summary": f"{t.category_name} stockout rose from {t.prior7_pct:.1f}% to {t.last7_pct:.1f}% "
                       f"week-over-week, the fastest-rising category.",
            "signals": [("At-risk category", str(t.category_name)), ("Now", f"{t.last7_pct:.1f}%"),
                        ("WoW", f"{t.delta_pts:+.1f} pts")],
            "chart": {"kind": "bar", "x": "category_name", "y": "last7_pct",
                      "title": "Stockout rate (%) by category, last 7 days"},
            "table": df, "recommendation": "Merchandising: prioritize replenishment for the rising category."}


def _fulfillment_risk(con, meta):
    w = _win(meta)
    df = _q(con, f"""SELECT f.region, g.carrier_group,
        round(avg(CASE WHEN date BETWEEN DATE '{w['l7']}' AND DATE '{w['td']}' THEN delay_days END),2) last7_delay,
        round(avg(CASE WHEN date BETWEEN DATE '{w['p7s']}' AND DATE '{w['p7e']}' THEN delay_days END),2) prior7_delay,
        round(avg(CASE WHEN date BETWEEN DATE '{w['l7']}' AND DATE '{w['td']}' THEN options_available END),1) avg_options
        FROM fact_fulfillment f JOIN dim_region g USING(region)
        GROUP BY f.region, g.carrier_group ORDER BY last7_delay DESC""")
    df["delta_days"] = (df.last7_delay - df.prior7_delay).round(2)
    t = df.iloc[0]
    return {"headline": f"Fulfillment risk: {t.region} delay {t.last7_delay:.2f}d "
                        f"({t.delta_days:+.2f}d WoW, carrier {t.carrier_group}).",
            "summary": f"{t.region} (carrier {t.carrier_group}) has the highest recent delay "
                       f"({t.last7_delay:.2f}d) with {t.avg_options:.1f} options on average.",
            "signals": [("At-risk region", str(t.region)), ("Delay", f"{t.last7_delay:.2f}d"),
                        ("WoW", f"{t.delta_days:+.2f}d")],
            "chart": {"kind": "bar", "x": "region", "y": "last7_delay",
                      "title": "Avg delivery delay (days) by region, last 7 days"},
            "table": df, "recommendation": "Fulfillment Operations: shore up options/SLAs in the at-risk region."}


def _cx_risk(con, meta):
    w = _win(meta)
    df = _q(con, f"""SELECT region,
        sum(CASE WHEN date BETWEEN DATE '{w['l7']}' AND DATE '{w['td']}' THEN 1 ELSE 0 END) last7,
        sum(CASE WHEN date BETWEEN DATE '{w['p7s']}' AND DATE '{w['p7e']}' THEN 1 ELSE 0 END) prior7
        FROM fact_customer_contacts GROUP BY region ORDER BY last7 DESC""")
    df["change_pct"] = ((df.last7 - df.prior7) / df.prior7.replace(0, 1) * 100).round(1)
    t = df.sort_values("change_pct", ascending=False).iloc[0]
    return {"headline": f"CX risk building in {t.region}: contacts {t.change_pct:+.1f}% week-over-week.",
            "summary": f"{t.region} contacts rose from {int(t.prior7)} to {int(t.last7)} "
                       f"({t.change_pct:+.1f}%), the fastest-rising region.",
            "signals": [("At-risk region", str(t.region)), ("Contacts (7d)", f"{int(t.last7):,}"),
                        ("WoW", f"{t.change_pct:+.1f}%")],
            "chart": {"kind": "bar", "x": "region", "y": "last7",
                      "title": "Customer contacts by region, last 7 days"},
            "table": df, "recommendation": "Customer Service: pre-empt the rising region; link to operations."}


def _vendor_risk(con, meta):
    w = _win(meta)
    df = _q(con, f"""SELECT s.vendor_id, any_value(v.vendor_name) vendor_name,
        round(sum(s.lost_sales_proxy),0) lost_sales,
        round(avg(s.stockout_impact)*100,1) stockout_impact_pct,
        round(avg(s.return_rate)*100,1) return_rate_pct, sum(s.service_issues)::BIGINT service_issues
        FROM fact_vendor_scorecard s JOIN dim_vendor v USING(vendor_id)
        WHERE s.date BETWEEN DATE '{w['l7']}' AND DATE '{w['td']}'
        GROUP BY s.vendor_id ORDER BY lost_sales DESC""")
    t = df.iloc[0]
    return {"headline": f"Vendor risk watch: {t.vendor_name} ({t.vendor_id}), "
                        f"${t.lost_sales:,.0f} lost-sales proxy (7d).",
            "summary": f"Over the last 7 days, {t.vendor_name} ({t.vendor_id}) tops the watch list with "
                       f"${t.lost_sales:,.0f} lost-sales proxy, {t.stockout_impact_pct:.1f}% stockout "
                       f"impact, {t.return_rate_pct:.1f}% return rate, and {int(t.service_issues):,} "
                       f"service issues.",
            "signals": [("Top vendor", f"{t.vendor_name} ({t.vendor_id})"),
                        ("Lost sales (7d)", f"${t.lost_sales:,.0f}"),
                        ("Stockout impact", f"{t.stockout_impact_pct:.1f}%"),
                        ("Service issues", f"{int(t.service_issues):,}")],
            "chart": {"kind": "bar", "x": "vendor_name", "y": "lost_sales",
                      "title": "Lost-sales proxy by vendor, last 7 days"},
            "table": df, "recommendation": "Merchandising: open a partner review with the top-risk vendor."}


THEMES = [
    # --- Health ---
    Theme("exec_briefing", "Executive: give me today's daily performance briefing.",
          "analytics", "Analytics / Leadership", _exec_briefing),
    Theme("cx_health", "Customer Service: run a customer-experience health check.",
          "service", "Customer Service", _cx_health),
    Theme("fulfillment_review", "Fulfillment: review fulfillment performance over the last two weeks.",
          "fulfillment", "Fulfillment Operations", _fulfillment_review),
    Theme("marketing_efficiency", "Marketing: review campaign spend efficiency across channels.",
          "marketing", "Marketing", _marketing_efficiency),
    Theme("revenue_quality", "Finance: review revenue quality (gross vs net and margin) over time.",
          "finance", "Finance", _revenue_quality),
    # --- Trend / anomaly ---
    Theme("trending_worse", "Analytics: what's trending worse week-over-week?",
          "analytics", "Digital Analytics", _trending_worse),
    Theme("unusual_spikes", "Analytics: are there any unusual spikes in the last 7 days?",
          "analytics", "Digital Analytics", _unusual_spikes),
    Theme("funnel_health", "Digital Analytics: how is checkout funnel health trending?",
          "analytics", "Digital Analytics", _funnel_health),
    # --- Risk ---
    Theme("stockout_risk", "Merchandising: which categories are at stockout risk?",
          "merchandising", "Merchandising", _stockout_risk),
    Theme("fulfillment_risk", "Fulfillment: which regions are at fulfillment risk?",
          "fulfillment", "Fulfillment Operations", _fulfillment_risk),
    Theme("cx_risk", "Customer Service: where is customer-experience risk building?",
          "service", "Customer Service", _cx_risk),
    Theme("vendor_risk", "Merchandising: which vendor partner is on the risk watch list?",
          "merchandising", "Merchandising", _vendor_risk),
]

_BY_ID = {t.id: t for t in THEMES}
_BY_Q = {t.question.lower(): t for t in THEMES}


def questions() -> list[str]:
    return [t.question for t in THEMES]


def match(question: str) -> str | None:
    return _BY_Q[question.strip().lower()].id if question.strip().lower() in _BY_Q else None


def get(theme_id: str) -> Theme | None:
    return _BY_ID.get(theme_id)


def run(theme_id: str, con, meta: dict) -> dict:
    th = _BY_ID[theme_id]
    out = th.build(con, meta)
    out.update({"id": th.id, "question": th.question, "owner": th.owner, "domain": th.domain})
    return out
