"""
Standalone governed analytics insights (NOT tied to the yesterday conversion-drop
investigation). Each insight is a realistic business question answered directly by
one read-only DuckDB query over the synthetic period, returning a result table,
key metrics, and a short numeric summary.

The workflow routes a question here (intent="analytics") when it matches one of
these insights; otherwise it runs the conversion-drop investigation. Every answer
directly addresses the asked question, surfaces 3-4 real numbers with proper
currency/%/decimal formatting, produces a chart that matches the question, and is
routed to an accountable owner.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass
class Insight:
    id: str
    question: str
    domain: str
    owner: str
    sql: str                       # may use {td} {l7} {b0} {b1} placeholders
    summarize: Callable            # (df) -> {headline, summary, metrics}


def _dates(meta: dict):
    td = dt.date.fromisoformat(meta["target_day"])
    return {"td": td.isoformat(), "l7": (td - dt.timedelta(days=6)).isoformat(),
            "b0": meta["baseline_start"], "b1": meta["baseline_end"]}


# ---- summarizers ---------------------------------------------------------
def _best_channel(df):
    t, lo = df.iloc[0], df.iloc[-1]
    return {"headline": f"Best-converting channel: {t.channel} at {t.conv_pct:.2f}%.",
            "summary": f"Across the period, {t.channel} converts highest at {t.conv_pct:.2f}% "
                       f"({int(t.sessions):,} sessions); {lo.channel} is lowest at {lo.conv_pct:.2f}%.",
            "metrics": [(r.channel, f"{r.conv_pct:.2f}%") for _, r in df.head(3).iterrows()]}


def _campaign_contribution(df):
    t = df.iloc[0]
    return {"headline": f"Campaign that converted below normal: {t.campaign_name} "
                        f"({t.conv_td_pct:.2f}% vs {t.conv_base_pct:.2f}% baseline).",
            "summary": f"On the target day, {t.campaign_name} ({t.channel}) drew {int(t.sessions):,} "
                       f"sessions but converted at {t.conv_td_pct:.2f}% versus a {t.conv_base_pct:.2f}% "
                       f"baseline — an estimated {abs(t.lost_orders):.0f} orders short of normal.",
            "metrics": [("Campaign", str(t.campaign_name)[:18]),
                        ("Conv vs base", f"{t.conv_td_pct:.2f}% / {t.conv_base_pct:.2f}%"),
                        ("Est. orders short", f"{abs(t.lost_orders):.0f}")]}


def _top_categories(df):
    t = df.iloc[0]
    return {"headline": f"Top category by sales (last 7 days): {t.category_name} (${t.sales:,.0f}).",
            "summary": "Sales over the last 7 days, ranked by category. "
                       f"{t.category_name} leads with ${t.sales:,.0f}; "
                       f"{df.iloc[-1].category_name} is lowest at ${df.iloc[-1].sales:,.0f}.",
            "metrics": [(r.category_name, f"${r.sales:,.0f}") for _, r in df.head(3).iterrows()]}


def _stockout_cat(df):
    t = df.iloc[0]
    return {"headline": f"Highest average stockout: {t.category_name} at {t.avg_stockout_pct:.1f}%.",
            "summary": f"Average stockout rate by category over the period. {t.category_name} is "
                       f"highest at {t.avg_stockout_pct:.1f}%; {df.iloc[-1].category_name} is lowest "
                       f"at {df.iloc[-1].avg_stockout_pct:.1f}%.",
            "metrics": [(r.category_name, f"{r.avg_stockout_pct:.1f}%") for _, r in df.head(3).iterrows()]}


def _top_vendors(df):
    t = df.iloc[0]
    return {"headline": f"Top vendor by revenue: {t.vendor_name} ({t.vendor_id}) at ${t.revenue:,.0f}.",
            "summary": f"Vendors ranked by item revenue. {t.vendor_name} ({t.vendor_id}) leads with "
                       f"${t.revenue:,.0f}; the top 3 together make ${df.head(3).revenue.sum():,.0f}.",
            "metrics": [(str(r.vendor_name)[:16], f"${r.revenue:,.0f}") for _, r in df.head(3).iterrows()]}


def _slowest_regions(df):
    t = df.iloc[0]
    return {"headline": f"Slowest delivery: {t.region} averaging {t.avg_delay_days:.2f} days late "
                        f"({t.carrier_group}).",
            "summary": f"Average delivery delay by region. {t.region} (zone {t.zone_id}, carrier "
                       f"{t.carrier_group}, owner {t.fulfillment_owner}) is slowest at "
                       f"{t.avg_delay_days:.2f} days with {t.avg_options:.1f} options on average.",
            "metrics": [(r.region, f"{r.avg_delay_days:.2f}d") for _, r in df.head(3).iterrows()]}


def _contact_reasons(df):
    t = df.iloc[0]
    total = int(df.contacts.sum())
    return {"headline": f"Top contact reason group: {t.reason_group} ({int(t.contacts):,} contacts).",
            "summary": f"{total:,} customer contacts over the period. '{t.reason_group}' is the top "
                       f"group at {int(t.contacts):,} ({t.contacts/total:.0%}); next is "
                       f"{df.iloc[1].reason_group} ({int(df.iloc[1].contacts):,}).",
            "metrics": [(r.reason_group, f"{int(r.contacts):,}") for _, r in df.head(3).iterrows()]}


def _contacts_per_order(df):
    t = df.iloc[0]
    return {"headline": f"Most contacts per order: {t.reason_group} at {t.per_order:.3f} per order.",
            "summary": f"Contacts per completed order by reason group. '{t.reason_group}' generates "
                       f"{t.per_order:.3f} contacts per order ({int(t.contacts):,} contacts); "
                       f"{df.iloc[-1].reason_group} is lowest at {df.iloc[-1].per_order:.3f}.",
            "metrics": [(r.reason_group, f"{r.per_order:.3f}/order") for _, r in df.head(3).iterrows()]}


def _net_trend(df):
    first, last = df.iloc[0], df.iloc[-1]
    chg = (last.net_revenue - first.net_revenue) / first.net_revenue if first.net_revenue else 0
    return {"headline": f"Net revenue {('up' if chg>=0 else 'down')} {abs(chg):.0%} over the period "
                        f"(${first.net_revenue:,.0f} → ${last.net_revenue:,.0f}).",
            "summary": f"Weekly net revenue trend across {len(df)} weeks; latest week "
                       f"${last.net_revenue:,.0f} net on ${last.gross_sales:,.0f} gross.",
            "metrics": [(str(r.week)[:10], f"${r.net_revenue:,.0f}") for _, r in df.tail(3).iterrows()]}


def _gross_to_net(df):
    r = df.iloc[0]
    pct = (r.gross - r.net) / r.gross if r.gross else 0
    return {"headline": f"Gross-to-net bridge: ${r.gross:,.0f} gross → ${r.net:,.0f} net "
                        f"({pct:.1%} reduction).",
            "summary": f"Recognized net revenue of ${r.net:,.0f} is ${r.gross - r.net:,.0f} below "
                       f"${r.gross:,.0f} gross sales, reduced by returns ${r.returns_total:,.0f}, "
                       f"discounts ${r.discounts:,.0f}, and adjustments ${r.adjustments:,.0f}. Tax "
                       f"${r.tax:,.0f} and shipping ${r.shipping:,.0f} are reported separately and "
                       f"are not part of merchandise net — neither source is wrong; they answer "
                       f"different reporting questions.",
            "metrics": [("Gross", f"${r.gross:,.0f}"), ("Returns", f"${r.returns_total:,.0f}"),
                        ("Discounts", f"${r.discounts:,.0f}"), ("Net", f"${r.net:,.0f}")]}


def _margin_proxy(df):
    t, lo = df.iloc[0], df.iloc[-1]
    return {"headline": f"Highest margin proxy: {t.category_name} at {t.margin_pct:.1f}%.",
            "summary": f"Margin proxy by category over the period. {t.category_name} is highest at "
                       f"{t.margin_pct:.1f}%; {lo.category_name} is lowest at {lo.margin_pct:.1f}% — "
                       f"a {t.margin_pct - lo.margin_pct:.1f} pt spread.",
            "metrics": [(r.category_name, f"{r.margin_pct:.1f}%") for _, r in df.head(3).iterrows()]}


def _vendor_scorecard(df):
    t = df.iloc[0]
    return {"headline": f"Alert vendor {t.vendor_name} ({t.vendor_id}): "
                        f"${t.lost_sales:,.0f} lost-sales proxy.",
            "summary": f"On the target day, {t.vendor_name} ({t.vendor_id}) carries the highest "
                       f"lost-sales proxy at ${t.lost_sales:,.0f}, with {t.stockout_impact_pct:.1f}% "
                       f"stockout impact, {t.return_rate_pct:.1f}% return rate, and "
                       f"{int(t.service_issues):,} service issues — flag the partner.",
            "metrics": [("Lost sales", f"${t.lost_sales:,.0f}"),
                        ("Stockout impact", f"{t.stockout_impact_pct:.1f}%"),
                        ("Service issues", f"{int(t.service_issues):,}")]}


def _aov_channel(df):
    t = df.iloc[0]
    return {"headline": f"Highest AOV channel: {t.channel} at ${t.avg_order_value:,.2f}.",
            "summary": f"Average order value by channel. {t.channel} is highest at "
                       f"${t.avg_order_value:,.2f} over {int(t.orders):,} orders; "
                       f"{df.iloc[-1].channel} is lowest at ${df.iloc[-1].avg_order_value:,.2f}.",
            "metrics": [(r.channel, f"${r.avg_order_value:,.2f}") for _, r in df.head(3).iterrows()]}


def _atc_device(df):
    t = df.iloc[0]
    return {"headline": f"Best add-to-cart rate: {t.device} at {t.add_to_cart_rate_pct:.1f}%.",
            "summary": f"Add-to-cart rate by device. {t.device} leads at "
                       f"{t.add_to_cart_rate_pct:.1f}%; {df.iloc[-1].device} is lowest at "
                       f"{df.iloc[-1].add_to_cart_rate_pct:.1f}%.",
            "metrics": [(r.device, f"{r.add_to_cart_rate_pct:.1f}%") for _, r in df.iterrows()]}


def _return_rate(df):
    t = df.iloc[0]
    return {"headline": f"Highest return rate: {t.category_name} at {t.return_rate_pct:.1f}% "
                        f"(${t.return_amount:,.0f} returned).",
            "summary": f"Return rate by category from the returns ledger. {t.category_name} is highest "
                       f"at {t.return_rate_pct:.1f}% ({int(t.return_count):,} returns on {int(t.orders):,} "
                       f"orders, ${t.return_amount:,.0f} returned).",
            "metrics": [(r.category_name, f"{r.return_rate_pct:.1f}%") for _, r in df.head(3).iterrows()]}


# ---- the analytics insights (one governed query each) --------------------
INSIGHTS = [
    # --- Marketing ---
    Insight("best_channel", "Marketing: which channel converts best over the period?",
            "marketing", "Marketing",
            "SELECT channel, count(*) AS sessions, "
            "round(sum(CASE WHEN converted THEN 1 ELSE 0 END)*100.0/count(*),2) AS conv_pct "
            "FROM fact_sessions GROUP BY channel ORDER BY conv_pct DESC", _best_channel),
    Insight("campaign_contribution",
            "Marketing: which campaign drove traffic that converted below normal?",
            "marketing", "Marketing",
            "WITH t AS (SELECT campaign_id, sum(sessions) AS s, sum(orders) AS o "
            "FROM fact_campaign_daily WHERE date=DATE '{td}' GROUP BY campaign_id), "
            "b AS (SELECT campaign_id, sum(orders)*1.0/nullif(sum(sessions),0) AS cr "
            "FROM fact_campaign_daily WHERE date BETWEEN DATE '{b0}' AND DATE '{b1}' GROUP BY campaign_id) "
            "SELECT k.campaign_name, k.channel, t.s::BIGINT AS sessions, "
            "round(t.o*100.0/nullif(t.s,0),2) AS conv_td_pct, round(b.cr*100,2) AS conv_base_pct, "
            "round((t.o*1.0/nullif(t.s,0) - b.cr)*t.s,1) AS lost_orders "
            "FROM t JOIN b USING(campaign_id) JOIN dim_campaign k USING(campaign_id) "
            "WHERE t.s >= 120 ORDER BY lost_orders ASC LIMIT 8", _campaign_contribution),
    # --- Merchandising ---
    Insight("top_categories_7d", "Merchandising: what were our top categories by sales last week?",
            "merchandising", "Merchandising",
            "SELECT c.category_name, round(sum(oi.item_amount),0) AS sales "
            "FROM fact_order_items oi JOIN fact_orders o ON oi.order_id=o.order_id "
            "JOIN dim_category c ON oi.category_id=c.category_id "
            "WHERE o.date BETWEEN DATE '{l7}' AND DATE '{td}' "
            "GROUP BY c.category_name ORDER BY sales DESC", _top_categories),
    Insight("stockout_cat", "Merchandising: what's the average stockout rate by category?",
            "merchandising", "Merchandising",
            "SELECT c.category_name, round(avg(stockout_rate)*100,1) AS avg_stockout_pct "
            "FROM fact_inventory_daily i JOIN dim_category c USING(category_id) "
            "GROUP BY c.category_name ORDER BY avg_stockout_pct DESC", _stockout_cat),
    Insight("top_vendors", "Merchandising: which vendors drive the most revenue?",
            "merchandising", "Merchandising",
            "SELECT p.vendor_id, any_value(v.vendor_name) AS vendor_name, "
            "round(sum(oi.item_amount),0) AS revenue "
            "FROM fact_order_items oi JOIN dim_product p ON oi.product_id=p.product_id "
            "JOIN dim_vendor v ON p.vendor_id=v.vendor_id "
            "GROUP BY p.vendor_id ORDER BY revenue DESC LIMIT 10", _top_vendors),
    # --- Fulfillment ---
    Insight("slowest_regions", "Fulfillment: which regions have the slowest delivery?",
            "fulfillment", "Fulfillment Operations",
            "SELECT f.region, g.zone_id, g.carrier_group, g.fulfillment_owner, "
            "round(avg(f.delay_days),2) AS avg_delay_days, round(avg(f.options_available),1) AS avg_options "
            "FROM fact_fulfillment f JOIN dim_region g USING(region) "
            "GROUP BY f.region, g.zone_id, g.carrier_group, g.fulfillment_owner "
            "ORDER BY avg_delay_days DESC", _slowest_regions),
    # --- Service ---
    Insight("contact_reasons", "Customer Service: what are the top contact reason groups?",
            "service", "Customer Service",
            "SELECT r.reason_group, count(*) AS contacts FROM fact_customer_contacts f "
            "JOIN dim_contact_reason r USING(reason_code) "
            "GROUP BY r.reason_group ORDER BY contacts DESC", _contact_reasons),
    Insight("contacts_per_order", "Customer Service: how many contacts per order does each reason drive?",
            "service", "Customer Service",
            "WITH o AS (SELECT count(*) AS n FROM fact_orders) "
            "SELECT r.reason_group, count(*) AS contacts, "
            "round(count(*)*1.0/(SELECT n FROM o),3) AS per_order "
            "FROM fact_customer_contacts f JOIN dim_contact_reason r USING(reason_code) "
            "GROUP BY r.reason_group ORDER BY per_order DESC", _contacts_per_order),
    # --- Finance ---
    Insight("net_trend", "Finance: how is net revenue trending week over week?",
            "finance", "Finance",
            "SELECT date_trunc('week', date) AS week, round(sum(net_revenue),0) AS net_revenue, "
            "round(sum(gross_sales),0) AS gross_sales FROM fact_finance_daily "
            "GROUP BY week ORDER BY week", _net_trend),
    Insight("gross_to_net", "Finance: what are the gross-to-net bridge components?",
            "finance", "Finance",
            "SELECT round(sum(gross_sales),0) AS gross, round(sum(returns),0) AS returns_total, "
            "round(sum(discounts),0) AS discounts, round(sum(adjustments),0) AS adjustments, "
            "round(sum(net_revenue),0) AS net, round(sum(tax),0) AS tax, "
            "round(sum(shipping),0) AS shipping "
            "FROM fact_finance_daily", _gross_to_net),
    Insight("margin_proxy", "Finance: what's the margin proxy by category?",
            "finance", "Finance",
            "SELECT c.category_name, round(avg(m.margin_proxy)*100,1) AS margin_pct "
            "FROM fact_margin_proxy_daily m JOIN dim_category c USING(category_id) "
            "GROUP BY c.category_name ORDER BY margin_pct DESC", _margin_proxy),
    # --- Vendor / Category ---
    Insight("vendor_scorecard", "Merchandising: which vendor or category partner should we alert?",
            "merchandising", "Merchandising",
            "SELECT s.vendor_id, any_value(v.vendor_name) AS vendor_name, "
            "round(sum(s.lost_sales_proxy),0) AS lost_sales, "
            "round(avg(s.stockout_impact)*100,1) AS stockout_impact_pct, "
            "round(avg(s.return_rate)*100,1) AS return_rate_pct, "
            "sum(s.service_issues)::BIGINT AS service_issues "
            "FROM fact_vendor_scorecard s JOIN dim_vendor v USING(vendor_id) "
            "WHERE s.date=DATE '{td}' GROUP BY s.vendor_id ORDER BY lost_sales DESC LIMIT 10",
            _vendor_scorecard),
    # --- Analytics ---
    Insight("aov_channel", "Analytics: what's the average order value by channel?",
            "analytics", "Digital Analytics",
            "SELECT channel, count(*) AS orders, round(avg(gross_amount),2) AS avg_order_value "
            "FROM fact_orders GROUP BY channel ORDER BY avg_order_value DESC", _aov_channel),
    Insight("atc_device", "Analytics: what's the add-to-cart rate by device?",
            "analytics", "Digital Analytics",
            "WITH e AS (SELECT device, "
            "sum(CASE WHEN event_type='product_view' THEN 1 ELSE 0 END) AS views, "
            "sum(CASE WHEN event_type='add_to_cart' THEN 1 ELSE 0 END) AS carts "
            "FROM fact_events GROUP BY device) "
            "SELECT device, round(carts*100.0/nullif(views,0),1) AS add_to_cart_rate_pct, views "
            "FROM e ORDER BY add_to_cart_rate_pct DESC", _atc_device),
    Insight("return_rate_cat", "Analytics: what's the return rate by category?",
            "analytics", "Merchandising",
            "WITH ords AS (SELECT category_id, count(*) AS orders FROM fact_orders GROUP BY category_id), "
            "rets AS (SELECT category_id, count(*) AS return_count, sum(return_amount) AS amt "
            "FROM fact_returns GROUP BY category_id) "
            "SELECT c.category_name, rets.return_count, ords.orders, "
            "round(rets.return_count*100.0/ords.orders,1) AS return_rate_pct, "
            "round(rets.amt,0) AS return_amount "
            "FROM rets JOIN ords USING(category_id) JOIN dim_category c USING(category_id) "
            "ORDER BY return_rate_pct DESC", _return_rate),
]

# chart spec per insight (column names match each query's output)
CHART_SPECS = {
    "best_channel": {"kind": "bar", "x": "channel", "y": "conv_pct", "title": "Conversion % by channel"},
    "campaign_contribution": {"kind": "bar", "x": "campaign_name", "y": "lost_orders",
                              "title": "Est. converted orders vs baseline by campaign (target day)"},
    "top_categories_7d": {"kind": "bar", "x": "category_name", "y": "sales", "title": "Sales by category (last 7 days)"},
    "stockout_cat": {"kind": "bar", "x": "category_name", "y": "avg_stockout_pct", "title": "Avg stockout % by category"},
    "top_vendors": {"kind": "bar", "x": "vendor_name", "y": "revenue", "title": "Revenue by vendor"},
    "slowest_regions": {"kind": "bar", "x": "region", "y": "avg_delay_days", "title": "Avg delivery delay (days) by region"},
    "contact_reasons": {"kind": "bar", "x": "reason_group", "y": "contacts", "title": "Contacts by reason group"},
    "contacts_per_order": {"kind": "bar", "x": "reason_group", "y": "per_order", "title": "Contacts per order by reason group"},
    "net_trend": {"kind": "line", "x": "week", "y": "net_revenue", "title": "Net revenue by week"},
    "gross_to_net": {"kind": "bridge", "title": "Gross-to-net bridge (period)"},
    "margin_proxy": {"kind": "bar", "x": "category_name", "y": "margin_pct", "title": "Margin proxy % by category"},
    "vendor_scorecard": {"kind": "bar", "x": "vendor_name", "y": "lost_sales", "title": "Lost-sales proxy by vendor (target day)"},
    "aov_channel": {"kind": "bar", "x": "channel", "y": "avg_order_value", "title": "Average order value by channel"},
    "atc_device": {"kind": "bar", "x": "device", "y": "add_to_cart_rate_pct", "title": "Add-to-cart rate % by device"},
    "return_rate_cat": {"kind": "bar", "x": "category_name", "y": "return_rate_pct", "title": "Return rate % by category"},
}

_BY_ID = {i.id: i for i in INSIGHTS}
_BY_Q = {i.question.lower(): i for i in INSIGHTS}


def questions() -> list[str]:
    return [i.question for i in INSIGHTS]


def match(question: str) -> str | None:
    """Return the insight id if the question matches one of the insights."""
    return _BY_Q[question.strip().lower()].id if question.strip().lower() in _BY_Q else None


def get(insight_id: str) -> Insight | None:
    return _BY_ID.get(insight_id)


def run(insight_id: str, con, meta: dict) -> dict:
    """Execute the insight's read-only query and return rendering data."""
    ins = _BY_ID[insight_id]
    sql = ins.sql.format(**_dates(meta))
    df = con.execute(sql).df()
    out = ins.summarize(df)
    out.update({"id": ins.id, "question": ins.question, "owner": ins.owner,
                "domain": ins.domain, "sql": sql, "table": df, "chart": CHART_SPECS.get(ins.id)})
    return out
