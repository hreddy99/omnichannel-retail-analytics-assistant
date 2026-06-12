"""
Standalone governed analytics insights (NOT tied to the yesterday conversion-drop
investigation). Each insight is a realistic business question answered directly by
one read-only DuckDB query over the synthetic period, returning a result table,
key metrics, and a short numeric summary.

The workflow routes a question here (intent="analytics") when it matches one of
these insights; otherwise it runs the conversion-drop investigation.
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
def _top_categories(df):
    t = df.iloc[0]
    return {"headline": f"Top category by sales (last 7 days): {t.category_name} (${t.sales:,.0f}).",
            "summary": "Sales over the last 7 days, ranked by category. "
                       f"{t.category_name} leads with ${t.sales:,.0f}; "
                       f"{df.iloc[-1].category_name} is lowest at ${df.iloc[-1].sales:,.0f}.",
            "metrics": [(r.category_name, f"${r.sales:,.0f}") for _, r in df.head(3).iterrows()]}


def _best_channel(df):
    t = df.iloc[0]
    return {"headline": f"Best-converting channel: {t.channel} at {t.conv_pct:.2f}%.",
            "summary": f"Across the period, {t.channel} converts highest at {t.conv_pct:.2f}% "
                       f"({int(t.sessions):,} sessions); {df.iloc[-1].channel} is lowest at "
                       f"{df.iloc[-1].conv_pct:.2f}%.",
            "metrics": [(r.channel, f"{r.conv_pct:.2f}%") for _, r in df.head(3).iterrows()]}


def _return_rate(df):
    t = df.iloc[0]
    return {"headline": f"Highest return rate: {t.category_name} at {t.return_rate_pct:.1f}%.",
            "summary": f"Return rate by category. {t.category_name} is highest at "
                       f"{t.return_rate_pct:.1f}% across {int(t.orders):,} orders.",
            "metrics": [(r.category_name, f"{r.return_rate_pct:.1f}%") for _, r in df.head(3).iterrows()]}


def _slowest_regions(df):
    t = df.iloc[0]
    return {"headline": f"Slowest delivery: {t.region} averaging {t.avg_delay_days:.2f} days late.",
            "summary": f"Average delivery delay by region. {t.region} is slowest "
                       f"({t.avg_delay_days:.2f} days, {t.avg_options:.1f} options on average).",
            "metrics": [(r.region, f"{r.avg_delay_days:.2f}d") for _, r in df.head(3).iterrows()]}


def _contact_reasons(df):
    t = df.iloc[0]
    total = int(df.contacts.sum())
    return {"headline": f"Top contact reason: {t.reason_code} ({int(t.contacts):,} contacts).",
            "summary": f"{total:,} customer contacts over the period. '{t.reason_code}' is the "
                       f"top reason at {int(t.contacts):,} ({t.contacts/total:.0%}).",
            "metrics": [(r.reason_code, f"{int(r.contacts):,}") for _, r in df.head(3).iterrows()]}


def _campaign_spend(df):
    t = df.iloc[0]
    return {"headline": f"Highest-spend campaign: {t.campaign_name} (${t.spend:,.0f}).",
            "summary": f"Campaigns by spend. {t.campaign_name} ({t.channel}) spent ${t.spend:,.0f} "
                       f"and drew {int(t.sessions):,} sessions.",
            "metrics": [(r.campaign_name[:18], f"${r.spend:,.0f}") for _, r in df.head(3).iterrows()]}


def _atc_device(df):
    t = df.iloc[0]
    return {"headline": f"Best add-to-cart rate: {t.device} at {t.add_to_cart_rate_pct:.1f}%.",
            "summary": f"Add-to-cart rate by device. {t.device} leads at "
                       f"{t.add_to_cart_rate_pct:.1f}%; {df.iloc[-1].device} is lowest at "
                       f"{df.iloc[-1].add_to_cart_rate_pct:.1f}%.",
            "metrics": [(r.device, f"{r.add_to_cart_rate_pct:.1f}%") for _, r in df.iterrows()]}


def _top_vendors(df):
    t = df.iloc[0]
    return {"headline": f"Top vendor by revenue: {t.vendor_id} ({t.brand}) at ${t.revenue:,.0f}.",
            "summary": f"Vendors ranked by item revenue. {t.vendor_id} ({t.brand}) leads with "
                       f"${t.revenue:,.0f}.",
            "metrics": [(f"{r.vendor_id}", f"${r.revenue:,.0f}") for _, r in df.head(3).iterrows()]}


def _net_trend(df):
    first, last = df.iloc[0], df.iloc[-1]
    chg = (last.net_revenue - first.net_revenue) / first.net_revenue if first.net_revenue else 0
    return {"headline": f"Net revenue {('up' if chg>=0 else 'down')} {abs(chg):.0%} over the period "
                        f"(${first.net_revenue:,.0f} → ${last.net_revenue:,.0f}).",
            "summary": f"Weekly net revenue trend across {len(df)} weeks; latest week "
                       f"${last.net_revenue:,.0f} net on ${last.gross_sales:,.0f} gross.",
            "metrics": [(str(r.week)[:10], f"${r.net_revenue:,.0f}") for _, r in df.tail(3).iterrows()]}


def _aov_channel(df):
    t = df.iloc[0]
    return {"headline": f"Highest AOV channel: {t.channel} at ${t.avg_order_value:,.2f}.",
            "summary": f"Average order value by channel. {t.channel} is highest at "
                       f"${t.avg_order_value:,.2f} over {int(t.orders):,} orders.",
            "metrics": [(r.channel, f"${r.avg_order_value:,.2f}") for _, r in df.head(3).iterrows()]}


def _stockout_cat(df):
    t = df.iloc[0]
    return {"headline": f"Highest average stockout: {t.category_name} at {t.avg_stockout_pct:.1f}%.",
            "summary": f"Average stockout rate by category over the period. {t.category_name} is "
                       f"highest at {t.avg_stockout_pct:.1f}%.",
            "metrics": [(r.category_name, f"{r.avg_stockout_pct:.1f}%") for _, r in df.head(3).iterrows()]}


# ---- the 11 insights -----------------------------------------------------
INSIGHTS = [
    Insight("top_categories_7d", "Merchandising: what were our top categories by sales last week?",
            "merchandising", "Merchandising",
            "SELECT c.category_name, round(sum(oi.item_amount),0) AS sales "
            "FROM fact_order_items oi JOIN fact_orders o ON oi.order_id=o.order_id "
            "JOIN dim_category c ON oi.category_id=c.category_id "
            "WHERE o.date BETWEEN DATE '{l7}' AND DATE '{td}' "
            "GROUP BY c.category_name ORDER BY sales DESC", _top_categories),
    Insight("best_channel", "Marketing: which channel converts best over the period?",
            "marketing", "Marketing",
            "SELECT channel, count(*) AS sessions, "
            "round(sum(CASE WHEN converted THEN 1 ELSE 0 END)*100.0/count(*),2) AS conv_pct "
            "FROM fact_sessions GROUP BY channel ORDER BY conv_pct DESC", _best_channel),
    Insight("return_rate_cat", "Merchandising: what's the return rate by category?",
            "merchandising", "Merchandising",
            "SELECT c.category_name, "
            "round(avg(CASE WHEN o.returned THEN 1.0 ELSE 0 END)*100,1) AS return_rate_pct, "
            "count(*) AS orders FROM fact_orders o JOIN dim_category c USING(category_id) "
            "GROUP BY c.category_name ORDER BY return_rate_pct DESC", _return_rate),
    Insight("slowest_regions", "Fulfillment: which regions have the slowest delivery?",
            "fulfillment", "Fulfillment Operations",
            "SELECT region, round(avg(delay_days),2) AS avg_delay_days, "
            "round(avg(options_available),1) AS avg_options FROM fact_fulfillment "
            "GROUP BY region ORDER BY avg_delay_days DESC", _slowest_regions),
    Insight("contact_reasons", "Customer Service: what are the top contact reasons?",
            "service", "Customer Service",
            "SELECT reason_code, count(*) AS contacts FROM fact_customer_contacts "
            "GROUP BY reason_code ORDER BY contacts DESC", _contact_reasons),
    Insight("campaign_spend", "Marketing: which campaigns have the highest spend vs traffic?",
            "marketing", "Marketing",
            "SELECT k.campaign_name, k.channel, k.spend, count(s.session_id) AS sessions "
            "FROM dim_campaign k LEFT JOIN fact_sessions s ON s.campaign_id=k.campaign_id "
            "WHERE k.campaign_id <> 'none' GROUP BY k.campaign_name, k.channel, k.spend "
            "ORDER BY k.spend DESC", _campaign_spend),
    Insight("atc_device", "Digital Analytics: what's the add-to-cart rate by device?",
            "analytics", "Digital Analytics",
            "WITH e AS (SELECT device, "
            "sum(CASE WHEN event_type='product_view' THEN 1 ELSE 0 END) AS views, "
            "sum(CASE WHEN event_type='add_to_cart' THEN 1 ELSE 0 END) AS carts "
            "FROM fact_events GROUP BY device) "
            "SELECT device, round(carts*100.0/nullif(views,0),1) AS add_to_cart_rate_pct, views "
            "FROM e ORDER BY add_to_cart_rate_pct DESC", _atc_device),
    Insight("top_vendors", "Merchandising: which vendors drive the most revenue?",
            "merchandising", "Merchandising",
            "SELECT p.vendor_id, any_value(p.brand) AS brand, round(sum(oi.item_amount),0) AS revenue "
            "FROM fact_order_items oi JOIN dim_product p ON oi.product_id=p.product_id "
            "GROUP BY p.vendor_id ORDER BY revenue DESC LIMIT 10", _top_vendors),
    Insight("net_trend", "Finance: how is net revenue trending week over week?",
            "finance", "Finance",
            "SELECT date_trunc('week', date) AS week, round(sum(net_revenue),0) AS net_revenue, "
            "round(sum(gross_sales),0) AS gross_sales FROM fact_finance_daily "
            "GROUP BY week ORDER BY week", _net_trend),
    Insight("aov_channel", "Analytics: what's the average order value by channel?",
            "analytics", "Digital Analytics",
            "SELECT channel, count(*) AS orders, round(avg(gross_amount),2) AS avg_order_value "
            "FROM fact_orders GROUP BY channel ORDER BY avg_order_value DESC", _aov_channel),
    Insight("stockout_cat", "Merchandising: what's the average stockout rate by category?",
            "merchandising", "Merchandising",
            "SELECT c.category_name, round(avg(stockout_rate)*100,1) AS avg_stockout_pct "
            "FROM fact_inventory_daily i JOIN dim_category c USING(category_id) "
            "GROUP BY c.category_name ORDER BY avg_stockout_pct DESC", _stockout_cat),
]

# chart spec per insight (column names match each query's output)
CHART_SPECS = {
    "top_categories_7d": {"kind": "bar", "x": "category_name", "y": "sales", "title": "Sales by category (last 7 days)"},
    "best_channel": {"kind": "bar", "x": "channel", "y": "conv_pct", "title": "Conversion % by channel"},
    "return_rate_cat": {"kind": "bar", "x": "category_name", "y": "return_rate_pct", "title": "Return rate % by category"},
    "slowest_regions": {"kind": "bar", "x": "region", "y": "avg_delay_days", "title": "Avg delivery delay (days) by region"},
    "contact_reasons": {"kind": "bar", "x": "reason_code", "y": "contacts", "title": "Contacts by reason"},
    "campaign_spend": {"kind": "bar", "x": "campaign_name", "y": "spend", "title": "Campaign spend"},
    "atc_device": {"kind": "bar", "x": "device", "y": "add_to_cart_rate_pct", "title": "Add-to-cart rate % by device"},
    "top_vendors": {"kind": "bar", "x": "vendor_id", "y": "revenue", "title": "Revenue by vendor"},
    "net_trend": {"kind": "line", "x": "week", "y": "net_revenue", "title": "Net revenue by week"},
    "aov_channel": {"kind": "bar", "x": "channel", "y": "avg_order_value", "title": "Average order value by channel"},
    "stockout_cat": {"kind": "bar", "x": "category_name", "y": "avg_stockout_pct", "title": "Avg stockout % by category"},
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
