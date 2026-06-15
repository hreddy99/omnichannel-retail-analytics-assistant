"""
Question-relevant charts for the Evidence view. `evidence_figure(trace)` returns a
Plotly figure matched to the question (conversion only for the overall question;
domain charts for driver questions; the insight/theme's own chart otherwise), so a
Customer-Service question shows contacts - not the conversion line.
"""
from __future__ import annotations

import plotly.graph_objects as go

_BLUE, _GREY, _RED, _GREEN = "#2563eb", "#94a3b8", "#dc2626", "#16a34a"


def _layout(fig, title, pct=False):
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10),
                      plot_bgcolor="white", title=title,
                      legend=dict(orientation="h", y=1.12))
    if pct:
        fig.update_yaxes(tickformat=".0%")
    return fig


def conversion_fig(series, baseline, target):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series["date"], y=series["conversion"], mode="lines+markers",
                             name="daily conversion", line=dict(color=_BLUE)))
    fig.add_hline(y=baseline, line_dash="dash", line_color=_GREY, annotation_text="prior 7-day avg")
    fig.add_trace(go.Scatter(x=[series["date"].iloc[-1]], y=[target], mode="markers",
                             marker=dict(size=14, color=_RED), name="yesterday"))
    return _layout(fig, "Digital conversion: daily vs prior 7-day average", pct=True)


def _bar(df, x, y, title, pct=False, color=_BLUE):
    fig = go.Figure(go.Bar(x=df[x].astype(str), y=df[y], marker_color=color))
    return _layout(fig, title, pct=pct)


def _grouped(df, x, series, title, pct=False):
    fig = go.Figure()
    for name, col, color in series:
        fig.add_trace(go.Bar(name=name, x=df[x].astype(str), y=df[col], marker_color=color))
    fig.update_layout(barmode="group")
    return _layout(fig, title, pct=pct)


def _line(df, x, y, title, pct=False):
    fig = go.Figure(go.Scatter(x=df[x].astype(str), y=df[y], mode="lines+markers",
                               line=dict(color=_BLUE)))
    return _layout(fig, title, pct=pct)


# driver focus key -> chart builder from that branch's evidence DataFrame
def _driver_fig(focus_key, ev):
    try:
        if focus_key == "campaign_mix":
            return _grouped(ev, "channel", [("baseline share", "share_base", _GREY),
                            ("yesterday share", "share_target", _BLUE)],
                            "Channel session share: baseline vs yesterday", pct=True)
        if focus_key == "inventory_availability":
            return _bar(ev.sort_values("stockout_target", ascending=False), "category_name",
                        "stockout_target", "Stockout rate by category (yesterday)", pct=True, color=_RED)
        if focus_key == "fulfillment_constraints":
            return _grouped(ev, "region", [("baseline delay (d)", "delay_base", _GREY),
                            ("yesterday delay (d)", "delay_target", _RED)],
                            "Delivery delay by region: baseline vs yesterday")
        if focus_key == "funnel_behavior":
            return _bar(ev, "category_name", "rate_target",
                        "Cart→purchase rate by category (yesterday)", pct=True)
        if focus_key == "service_signal":
            return _bar(ev.sort_values("contacts_target", ascending=False), "reason_code",
                        "contacts_target", "Customer contacts by reason (yesterday)", color=_RED)
        if focus_key == "vendor_insight":
            d = ev.copy(); d["vendor"] = d["vendor_id"].astype(str) + " / " + d["category_id"].astype(str)
            return _bar(d.head(8), "vendor", "impact",
                        "Sales-weighted stockout impact by vendor", color=_RED)
        if focus_key == "finance_caveat":
            r = ev.iloc[0]
            fig = go.Figure(go.Bar(x=["gross", "net", "returns"],
                                   y=[float(r.gross_t), float(r.net_t), float(r.returns_t)],
                                   marker_color=[_BLUE, _GREEN, _RED]))
            return _layout(fig, "Gross vs net vs returns (yesterday)")
    except Exception:
        return None
    return None


def _bridge(df, title):
    """Gross-to-net bridge: gross less the deductions that actually reduce net
    (returns, discounts, adjustments) arriving at net revenue (one-row df). Tax and
    shipping are reported separately and are not part of merchandise net."""
    r = df.iloc[0]
    labels = ["gross", "− returns", "− discounts", "± adjustments", "net"]
    vals = [float(r.gross), float(r.returns_total), float(r.discounts),
            float(r.adjustments), float(r.net)]
    colors = [_BLUE, _RED, _RED, _GREY, _GREEN]
    fig = go.Figure(go.Bar(x=labels, y=vals, marker_color=colors))
    return _layout(fig, title)


def briefing_fig(issues):
    """Cross-domain executive briefing: evidence score (0-14) per issue, colored by
    priority (Act now = red, otherwise blue)."""
    if not issues:
        return None
    issues = list(issues)[:8]
    labels = [i["label"] for i in issues]
    scores = [i.get("score", 0) for i in issues]
    colors = [_RED if i.get("priority") == "high" else _BLUE for i in issues]
    fig = go.Figure(go.Bar(x=labels, y=scores, marker_color=colors))
    fig.update_yaxes(range=[0, 14], title="evidence score (/14)")
    return _layout(fig, "Cross-functional issues ranked by evidence strength")


def from_spec(df, spec):
    """Build a fig from a chart spec dict: {kind, x, y, title, pct?}."""
    if df is None or spec is None or len(df) == 0:
        return None
    kind = spec.get("kind", "bar")
    title = spec.get("title", "")
    pct = spec.get("pct", False)
    try:
        if kind == "line":
            return _line(df, spec["x"], spec["y"], title, pct=pct)
        if kind == "grouped":
            return _grouped(df, spec["x"], spec["series"], title, pct=pct)
        if kind == "bridge":
            return _bridge(df, title)
        return _bar(df, spec["x"], spec["y"], title, pct=pct)
    except Exception:
        return None


def evidence_figure(t):
    """Pick the chart that matches the question. Returns a Plotly figure or None."""
    a = t.get("answer", {})
    intent = a.get("intent", "overall")
    if intent == "overall" and t.get("baseline"):
        bl = t["baseline"]
        return conversion_fig(bl["series"], bl["baseline"], bl["target"])
    if intent == "briefing":
        return briefing_fig(a.get("briefing_issues"))
    if intent == "driver" and a.get("focus"):
        return _driver_fig(a["focus"].get("key") or _focus_key(t), a["focus"].get("evidence"))
    if intent in ("analytics", "themed") and a.get("chart"):
        return from_spec(a.get("table"), a["chart"])
    return None


def _focus_key(t):
    """Recover the driver key for the focused branch (focus block stores label)."""
    label = t["answer"]["focus"]["label"]
    for b in t.get("depth1", []):
        if b.label == label:
            return b.driver
    return None
