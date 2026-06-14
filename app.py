"""
Omnichannel Retail Analytics Assistant - Streamlit app.

Interactive companion to the detailed project plan AND a runnable prototype of
the governed investigation workflow (ReAct + RAG + Knowledge Graph + conditional
ToT beam search). The Live Demo runs the real LangGraph pipeline and exposes the
four trace levels from Plan section 17.3.

Run:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import agent_specs, catalog, charts, graph, guardrails, insights, llm, themes
from src import plan_content as P
from src import retrieval
from src.investigation import BEAM_WIDTH, QUERY_BUDGET, run_investigation, run_investigation_stream

st.set_page_config(page_title="Omnichannel Retail Analytics Assistant",
                   page_icon="🛍️", layout="wide")

CONF_COLOR = {"likely driver": "#16a34a", "possible contributor": "#d97706",
              "possible contributor (outside beam)": "#d97706", "pruned": "#dc2626"}


def _table(rows, cols):
    st.dataframe(pd.DataFrame(rows, columns=cols), width="stretch", hide_index=True)


_CCY = ("sales", "revenue", "gross", "net", "spend", "returns", "amount", "impact")


def _col_fmt(name, s):
    """Return a pandas format string/callable for a column based on its name/values."""
    n = str(name).lower()
    try:
        kind = s.dtype.kind
    except Exception:
        kind = "O"
    if kind not in "if":
        return None
    if any(k in n for k in ("price", "order_value", "aov")):
        return "${:,.2f}"
    if any(k in n for k in _CCY) and "rate" not in n and "pct" not in n:
        return "${:,.0f}"
    if any(k in n for k in ("pct", "rate", "share", "conv")):
        mx = float(s.dropna().abs().max()) if len(s.dropna()) else 0.0
        return (lambda v: f"{v * 100:.1f}%") if mx <= 1.5 else "{:.1f}%"
    if any(k in n for k in ("delay", "days", "option")):
        return "{:.2f}"
    if kind == "i":
        return "{:,.0f}"
    return "{:,.2f}"


def show_df(df):
    """Render a DataFrame with proper currency/decimal/percent formatting."""
    if df is None or len(df) == 0:
        st.caption("No rows.")
        return
    fmt = {c: f for c in df.columns if (f := _col_fmt(c, df[c])) is not None}
    try:
        st.dataframe(df.style.format(fmt), width="stretch", hide_index=True)
    except Exception:
        st.dataframe(df, width="stretch", hide_index=True)


@st.cache_resource(show_spinner="Building local vector index (ChromaDB)…")
def _index():
    return retrieval.get_index()


# ==========================================================================
# PAGE: Overview
# ==========================================================================
def page_overview():
    st.title("🛍️ Omnichannel Retail Analytics Assistant")
    st.caption(f"{P.SUBTITLE}  ·  {P.TAGLINE}")
    st.success("**Feasibility decision:** " + P.FEASIBILITY)
    st.subheader("Executive summary")
    st.write(P.EXECUTIVE_SUMMARY)
    st.subheader("Business problem & intended users")
    st.write(P.BUSINESS_PROBLEM)
    _table(P.BUSINESS_ROLES, ["Business role", "Typical question", "Assistant value"])

    st.subheader("Enterprise analytics & modern data platform")
    st.write(P.ENTERPRISE_ALIGNMENT)
    _table(P.MEDALLION, ["Medallion layer", "Role"])
    st.caption(P.MEDALLION_NOTE)
    st.markdown("**Enterprise value**")
    for v in P.ENTERPRISE_VALUE:
        st.markdown(f"- {v}")

    st.subheader("Agentic capability alignment")
    _table(P.CAPABILITY_ALIGNMENT, ["Capability", "How the assistant implements it", "What good looks like"])
    st.subheader("Implementation status")
    status = pd.DataFrame(P.PROTOTYPE_STATUS, columns=["Component", "Status", "Notes"])
    color = {"Built": "background-color:#dcfce7", "Optional": "background-color:#e0e7ff"}
    st.dataframe(status.style.map(lambda s: color.get(s, ""), subset=["Status"]),
                 width="stretch", hide_index=True)


# ==========================================================================
# PAGE: Feasibility
# ==========================================================================
def page_feasibility():
    st.title("✅ Feasibility Review")
    st.write("The plan's core claim is a **free, local, read-only** MVP runnable on a "
             "personal PC. This prototype confirms it end-to-end.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Required paid services", "0")
    c2.metric("External APIs to run demo", "0")
    c3.metric("Runs locally", "Yes")
    st.info("**Verdict: Feasible.** The Live Demo runs the full governed workflow "
            "(Faker synthetic data → ChromaDB retrieval → NetworkX graph → DuckDB evidence "
            "→ conditional ToT beam search → guardrails → grounded answer) with free, local "
            "tools. Ollama (LLM) and sentence-transformers downloads are optional enhancements "
            "with graceful fallbacks, so the architecture is demonstrable on any laptop.")
    st.subheader("Free / local tool stack")
    rows = [(t, r, ("✅ " + f if f == "Yes" else "🔵 " + f), n) for (t, r, f, n) in P.TOOL_STACK]
    _table(rows, ["Tool", "Role", "Free / on PC?", "MVP notes"])

    st.subheader("Implementation issues found in this hosted sandbox (and how they're handled)")
    st.markdown(
        "- **Ollama** needs a separate daemon + multi-GB model — not present in a cloud "
        "sandbox. Handled: optional client with a deterministic template fallback (works on your PC).\n"
        "- **sentence-transformers** downloads its model from huggingface.co, which is blocked "
        "here. Handled: falls back to ChromaDB's bundled ONNX build of the **same all-MiniLM-L6-v2** "
        "model, then to a deterministic hashing embedder.\n"
        "- **ChromaDB** install collided with the system PyYAML. Handled: documented install flag.\n"
        "- The **active embedder and LLM mode are shown in Trust details** so degradation is visible.")

    st.subheader("Implementation-readiness checklist")
    _table(P.READINESS, ["Question", "Answer"])
    st.subheader("Risks & mitigations")
    _table(P.RISKS, ["Risk", "Mitigation"])


# ==========================================================================
# PAGE: Architecture
# ==========================================================================
def _flow_figure():
    nodes = ["Question", "Classify", "Sync\ngate", "Retrieve\n(Chroma)", "Validate\n(YAML)",
             "Relate\n(graph)", "Baseline\n(DuckDB)", "ToT\ngate", "Beam\nsearch",
             "Evidence\ngate", "Answer"]
    xs = list(range(len(nodes)))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=[0] * len(nodes), mode="markers+text",
                             marker=dict(size=42, color="#2563eb", line=dict(width=2, color="#1e40af")),
                             text=nodes, textposition="middle center",
                             textfont=dict(color="white", size=9), hoverinfo="text"))
    for i in range(len(nodes) - 1):
        fig.add_annotation(x=xs[i + 1], y=0, ax=xs[i], ay=0, xref="x", yref="y", axref="x",
                           ayref="y", showarrow=True, arrowhead=3, arrowwidth=1.5, arrowcolor="#94a3b8")
    fig.add_annotation(x=4, y=0, ax=9, ay=0.5, xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowwidth=1.2, arrowcolor="#f59e0b",
                       text="revise / retry", font=dict(size=9, color="#b45309"))
    fig.update_layout(height=210, showlegend=False, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(visible=False, range=[-0.6, len(nodes) - 0.4]),
                      yaxis=dict(visible=False, range=[-0.7, 0.8]), plot_bgcolor="white")
    return fig


def _graph_figure():
    import networkx as nx
    g = graph.build_graph()
    pos = nx.spring_layout(g, seed=11, k=1.1)
    kind_color = {"metric": "#2563eb", "driver": "#16a34a", "table": "#64748b",
                  "owner": "#d97706", "system": "#9333ea"}
    ex, ey = [], []
    for u, v in g.edges():
        ex += [pos[u][0], pos[v][0], None]; ey += [pos[u][1], pos[v][1], None]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line=dict(width=0.8, color="#cbd5e1"),
                             hoverinfo="none", showlegend=False))
    for kind, color in kind_color.items():
        ns = [n for n in g.nodes if g.nodes[n].get("kind") == kind]
        if not ns:
            continue
        fig.add_trace(go.Scatter(x=[pos[n][0] for n in ns], y=[pos[n][1] for n in ns],
                                 mode="markers+text", name=kind, marker=dict(size=14, color=color),
                                 text=[g.nodes[n].get("label", n) for n in ns],
                                 textposition="top center", textfont=dict(size=8), hoverinfo="text"))
    fig.update_layout(height=520, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(visible=False),
                      yaxis=dict(visible=False), legend=dict(orientation="h", y=1.04), plot_bgcolor="white")
    return fig


def page_architecture():
    st.title("🏗️ Architecture")
    st.write("LangGraph is the central controller. Tools and knowledge layers do not act "
             "independently — retrieval, validation, graph traversal, ToT, SQL, and synthesis "
             "are explicit workflow nodes. YAML governs truth; the LLM is never a source of truth.")
    st.subheader("Controller flow (LangGraph state machine)")
    st.plotly_chart(_flow_figure(), width="stretch")
    st.subheader("Architecture layers")
    _table(P.ARCH_LAYERS, ["Layer", "Component", "Responsibility", "Implementation control"])
    st.subheader("Relationship to surrounding OLTP systems")
    st.caption("The assistant analyzes the governed analytical copy of this data and produces "
               "human-reviewed recommendations — it never updates transactional systems.")
    _table(P.OLTP_RELATIONSHIP, ["Source / OLTP system", "Enterprise analytics role", "Assistant use"])
    st.subheader("Knowledge graph generated from the YAML catalog (NetworkX)")
    st.caption(f"Live render of the catalog (v{catalog.version()}, hash {catalog.content_hash()}). "
               "metric → driver → table / system / owner.")
    st.plotly_chart(_graph_figure(), width="stretch", key="arch_graph")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("YAML catalog files")
        _table(P.YAML_FILES, ["File", "Contents", "Used by"])
        st.subheader("Graph objects")
        _table(P.GRAPH_OBJECTS, ["Object", "Examples", "Purpose"])
    with col2:
        st.subheader("Agent roles")
        _table(P.AGENT_ROLES, ["Agent / role", "Purpose", "Primary tools", "MVP output"])
        st.subheader("Source-conflict & priority rules")
        _table(P.CONFLICT_RULES, ["Situation", "Decision rule", "User-facing behavior"])

    st.subheader("Multi-agent team — specialization, parallelism & deliberate trade-offs")
    st.write(P.MULTI_AGENT_INTRO)
    mc1, mc2 = st.columns(2)
    with mc1:
        st.markdown("**Specialized analyst team**")
        _table(P.ANALYST_TEAM, ["Analyst", "Domain", "Governed driver / focus"])
    with mc2:
        st.markdown("**When we use multiple agents (and when we don't)**")
        _table(P.MULTI_AGENT_WHEN, ["Decision", "Rationale"])
        st.markdown("**Trade-offs accepted & mitigations**")
        _table(P.MULTI_AGENT_TRADEOFFS, ["Trade-off", "Mitigation"])


# ==========================================================================
# PAGE: Step-by-Step Plan
# ==========================================================================
def page_plan():
    st.title("🗺️ Step-by-Step Implementation Plan")
    st.subheader("Capability roadmap")
    _table(P.PHASE_ROADMAP, ["Stage", "Primary objective", "Scope", "Success criteria"])
    st.subheader("Implementation milestones")
    built = {"1", "2", "3", "4", "5", "6", "7", "8", "9"}
    rows = [(ph, d, ex, "✅ Built" if ph.split(".")[0] in built else "⬜ Backlog")
            for ph, d, ex in P.MILESTONES]
    _table(rows, ["Milestone", "Deliverables", "Exit criteria", "Prototype status"])
    st.subheader("Conditional Tree-of-Thought — depth model")
    _table(P.TOT_DEPTH, ["ToT element", "Definition in this project"])
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("ToT scoring rubric")
        rub = [(c, f"0–{m}") for c, m in P.TOT_RUBRIC]
        rub.append(("**Maximum total**", f"**{sum(m for _, m in P.TOT_RUBRIC)}**"))
        _table(rub, ["Evaluation criterion", "Score"])
        st.caption(P.TOT_THRESHOLDS)
    with c2:
        st.subheader("Synthetic tables")
        _table(P.SYNTH_TABLES, ["Table", "Grain", "Role"])
    st.subheader("Seeded demo scenarios")
    _table(P.SCENARIOS, ["Seeded scenario", "Injected pattern", "Expected evidence", "Owner"])
    st.subheader("Functional requirements")
    _table(P.FUNC_REQS, ["ID", "Requirement", "Priority", "Acceptance criteria"])
    with st.expander("Non-functional requirements"):
        _table(P.NON_FUNCTIONAL, ["Area", "Requirement"])
    st.subheader("MVP demo questions")
    for i, q in enumerate(P.DEMO_QUESTIONS, 1):
        st.markdown(f"{i}. {q}")


# ==========================================================================
# PAGE: Live Demo
# ==========================================================================
def _scorecard(b):
    color = CONF_COLOR.get(b.confidence, "#64748b")
    st.markdown(f"<div style='border-left:5px solid {color};padding:6px 12px;margin:6px 0;"
                f"background:#f8fafc;border-radius:4px'><b>{b.label}</b> · score "
                f"<b>{b.total}/14</b> · <span style='color:{color}'><b>{b.confidence}</b></span>"
                f"<br><span style='font-size:0.9em;color:#475569'>{b.finding}</span></div>",
                unsafe_allow_html=True)


def _driver_block(a):
    """Render the cross-domain driver findings (used for the overall question and
    inside an expander for focused questions)."""
    st.markdown("**Likely drivers (selected by beam search):**")
    for d in a["drivers"]:
        c = CONF_COLOR.get(d["confidence"], "#16a34a")
        st.markdown(f"<div style='border-left:5px solid {c};padding:6px 12px;margin:5px 0;"
                    f"background:#f0fdf4;border-radius:4px'><b>{d['label']}</b> → <b>{d['owner']}</b> · "
                    f"<span style='color:{c}'>{d['confidence']}</span> (score {d['score']}/14)<br>"
                    f"<span style='font-size:0.9em;color:#475569'>{d['finding']}</span></div>",
                    unsafe_allow_html=True)
    if a["contributors"]:
        st.markdown("**Possible contributors (outside the beam):**")
        for d in a["contributors"]:
            st.markdown(f"- **{d['label']}** → {d['owner']} (score {d['score']}/14) — {d['finding']}")
    if a.get("corroborating"):
        st.markdown("**Corroborating signals (secondary — not direct causes):**")
        for d in a["corroborating"]:
            st.markdown(f"- **{d['label']}** → {d['owner']} — {d['finding']}")
    if a["pruned"]:
        st.markdown("**Pruned hypotheses:**")
        for p in a["pruned"]:
            st.markdown(f"- ~~{p['label']}~~ (score {p['score']}/14) — {p['reason']}")


def _tab_business(t):
    a = t["answer"]; bl = t["baseline"]; intent = a.get("intent", "overall")
    st.markdown(f"### {a['headline']}")
    st.caption("Level 1 · Business summary — for business users and leaders")
    conf_c = "#16a34a" if a["confidence"] == "high" else "#d97706"
    st.markdown(f"**Confidence:** <span style='color:{conf_c}'>{a['confidence']}</span>  ·  "
                f"*drafting: {a.get('llm_mode')}*", unsafe_allow_html=True)
    st.write(a["summary"])
    if intent not in (None, "overall") and a.get("conversion_context"):
        st.caption("Context: " + a["conversion_context"])

    if intent in ("analytics", "themed"):
        mets = a.get("metrics") or a.get("signals", [])
        if mets:
            cols = st.columns(min(len(mets), 4))
            for col, (label, val) in zip(cols, mets[:4]):
                col.metric(str(label), str(val))
        fig = charts.evidence_figure(t)
        if fig is not None:
            st.plotly_chart(fig, width="stretch", key="biz_main_chart")
        if a.get("table") is not None:
            st.markdown("**Result (read-only DuckDB query):**")
            show_df(a["table"])
        st.info(f"**Owner:** {a.get('owner', '-')} · {a.get('recommendation', '')}")
        return

    if intent == "overall":
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Yesterday", f"{bl['target']:.2%}")
        m2.metric("Prior 7-day avg", f"{bl['baseline']:.2%}")
        m3.metric("Change", f"{bl['pct_change']:+.1%}")
        m4.metric("Queries used", f"{t['queries_used']}/{QUERY_BUDGET}")
        _driver_block(a)
        st.info("**Recommendation:** " + a["recommendation"])

    elif intent == "driver" and a.get("focus"):
        f = a["focus"]
        c = CONF_COLOR.get(f["confidence"], "#16a34a")
        st.markdown(f"<div style='border-left:5px solid {c};padding:8px 14px;margin:6px 0;"
                    f"background:#f0fdf4;border-radius:4px'><b>{f['label']}</b> → <b>{f['owner']}</b> · "
                    f"<span style='color:{c}'>{f['confidence']}</span><br>"
                    f"<span style='font-size:0.92em;color:#334155'>{f['finding']}</span></div>",
                    unsafe_allow_html=True)
        fig = charts.evidence_figure(t)
        if fig is not None:
            st.plotly_chart(fig, width="stretch", key="biz_focus_chart")
        if f.get("evidence") is not None:
            st.markdown("**Evidence (read-only DuckDB):**")
            show_df(f["evidence"])
        st.info(f"**Recommended action — {f['owner']}:** {f['action']}")
        with st.expander("See the full cross-domain investigation"):
            _driver_block(a)

    elif intent == "actions":
        st.markdown("**Recommended actions by owner:**")
        rows = [{"owner": r["owner"], "priority": r["priority"], "action": r["action"],
                 "basis": r["rationale"]} for r in a["exec_summary"]["recommendations"]]
        if rows:
            show_df(pd.DataFrame(rows))
        with st.expander("See the supporting driver findings"):
            _driver_block(a)

    elif intent == "trust":
        st.markdown(f"**Certified metric definition:** {a['definition']}")
        st.caption("Baseline rule: prior 7-day average. See the **Trust details** tab for retrieved "
                   "context, graph path, catalog version/hash, and the active embedder.")

    elif intent == "caveats":
        st.markdown("**Caveats & data-freshness limits:**")
        for cv in a["caveats"]:
            st.markdown(f"- {cv}")

    es = a.get("exec_summary")
    if es:
        st.markdown(f"#### {es['title']}")
        for line in es["bullets"]:
            st.markdown(f"- {line}")
        st.caption(es["note"])


def _tab_evidence(t):
    st.caption("Level 2 · Evidence summary — for analysts and managers")
    a = t["answer"]
    # Chart matched to the question (conversion only for the overall question).
    fig = charts.evidence_figure(t)
    if fig is not None:
        st.plotly_chart(fig, width="stretch", key="evidence_chart")
    if a.get("intent") in ("analytics", "themed"):
        if a.get("table") is not None:
            show_df(a["table"])
        if a.get("sql"):
            with st.expander("Query (read-only, validated)"):
                st.code(a["sql"], language="sql")
        return
    if t.get("depth1"):
        st.markdown("**Per-driver evidence (read-only DuckDB):**")
        for b in t["depth1"]:
            if b.evidence is None:
                continue
            with st.expander(f"{b.label} — evidence ({b.confidence})"):
                show_df(b.evidence)


def _tab_trust(t):
    st.caption("Level 3 · Trust details — for analysts, reviewers, stakeholder demo")
    a = t["answer"]
    st.markdown(f"**Selected YAML metric definition:** {a['definition']}")
    st.markdown(f"**Catalog version / hash:** v{t['catalog_version']} · `{t['catalog_hash']}`")
    idx = _index()
    sync = idx.sync_status()
    c1, c2, c3 = st.columns(3)
    c1.metric("Vector embedder", sync["embedder"].split("/")[0])
    c2.metric("Index in sync", "Yes" if sync["in_sync"] else "No")
    c3.metric("LLM mode", a.get("llm_mode", "n/a").split(":")[0])
    st.caption(f"Embedder: {sync['embedder']} · {sync['n_chunks']} governed chunks indexed.")
    st.markdown("**Retrieved context (top-k from ChromaDB):**")
    if t["retrieval"]:
        rows = [{"source_type": r["metadata"].get("source_type"), "name": r["metadata"].get("name"),
                 "owner": r["metadata"].get("owner"), "version": r["metadata"].get("version"),
                 "validated_vs_yaml": r["validated"], "distance": round(r["distance"], 3)}
                for r in t["retrieval"]]
        show_df(pd.DataFrame(rows))
    st.markdown("**Graph path (NetworkX):**")
    g = graph.build_graph()
    for b in t["beam"]:
        gp = graph.driver_path(g, b.driver)
        if gp:
            st.markdown(f"- `{gp['path']}`  → system: {gp.get('system')}")
    st.markdown("**Caveats:**")
    for cv in a["caveats"]:
        st.markdown(f"- {cv}")


def _tab_tot(t):
    st.caption("Level 3 · ToT trace — candidate branches, scores, pruning, selection")
    if not t["tot_activated"]:
        st.info("ToT not activated for this question (single obvious path).")
        return
    st.markdown(f"**Primary-driver beam (kept top {len(t['beam'])}):**")
    for b in t["beam"]:
        _scorecard(b)
        with st.expander(f"Score breakdown & SQL — {b.label}"):
            st.dataframe(pd.DataFrame([{"criterion": k, "score": v} for k, v in b.scores.items()]),
                         width="stretch", hide_index=True)
            if getattr(b, "evidence_gated", False):
                st.caption("⚠ Evidence strength gated to 0 — structural checks (metric+graph+SQL) "
                           "scored below the threshold, so strong evidence cannot carry this branch.")
            if b.sql:
                st.code(b.sql, language="sql")
    if t["deferred"]:
        st.markdown("**Deferred primary drivers (qualified, outside beam):**")
        for b in t["deferred"]:
            _scorecard(b)
    if t.get("corroborating"):
        st.markdown("**Corroborating signals (secondary — service / finance / vendor):**")
        for b in t["corroborating"]:
            _scorecard(b)
    if t["pruned"]:
        st.markdown("**Pruned (below threshold / ungoverned):**")
        for b in t["pruned"]:
            _scorecard(b)
    if t["depth2"]:
        st.markdown("**Depth-2 refinement:**")
        for d in t["depth2"]:
            st.markdown(f"- {d['refined']}")


def _tab_audit(t):
    st.caption("Level 4 · Technical audit — LangGraph nodes, tool calls, SQL validation")
    audit = t["audit"]
    st.markdown(f"**run_id:** `{audit.run_id}`  ·  **events:** {len(audit.events)}  ·  "
                f"**queries:** {t['queries_used']}/{QUERY_BUDGET}")
    st.markdown("**Decision log (step-by-step):**")
    for s in t["steps"]:
        st.markdown(f"{'✅' if s['ok'] else '⚠️'} **{s['node']}** — {s['detail']}")
    st.markdown("**Audit event trail (section 17.2 schema):**")
    cols = ["event_id", "workflow_node", "decision_type", "tool_name", "output_summary",
            "score_or_confidence", "status"]
    st.dataframe(pd.DataFrame(audit.events)[cols], width="stretch", hide_index=True)
    sql = t["baseline"].get("sql") if t["baseline"] else t["answer"].get("sql")
    if sql:
        with st.expander("Primary SQL (read-only, validated)"):
            ok, reason = guardrails.check_sql(sql)
            st.code(sql, language="sql")
            st.caption(("✅ " if ok else "⚠️ ") + reason)


def _tab_actions(t):
    st.caption("Action log — human-reviewed recommendations only; no operational writes")
    actions = t["audit"].actions
    if actions:
        show_df(pd.DataFrame(actions))
    st.warning("Recommended actions are for human review only. The assistant never writes to "
               "ERP, OMS, CRM, pricing, inventory, campaign, fulfillment, service, or finance systems.")


def _tab_team(t):
    st.caption("Multi-agent team — specialized analysts dispatched in parallel by the Orchestrator")
    coord = t.get("coordination", {})
    if not coord:
        st.info("No team dispatched for this run.")
        return
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Analysts", coord.get("n_agents", 0))
    c2.metric("Succeeded", coord.get("n_ok", 0))
    c3.metric("Failed", coord.get("n_failed", 0))
    c4.metric("Parallel speedup", f"{coord.get('speedup', 1)}×")
    st.caption(f"Wall-clock {coord.get('wall_ms', 0)} ms in parallel vs "
               f"{coord.get('sequential_ms', 0)} ms if run one-by-one.")
    # parallel execution timeline (per-agent durations)
    tl = coord.get("timeline", [])
    if tl:
        fig = go.Figure(go.Bar(
            x=[r["elapsed_ms"] for r in tl], y=[r["agent"] for r in tl], orientation="h",
            marker_color=["#16a34a" if r["status"] == "ok" else "#dc2626" for r in tl],
            text=[r["status"] for r in tl], textposition="auto"))
        fig.update_layout(height=40 + 32 * len(tl), margin=dict(l=10, r=10, t=24, b=10),
                          plot_bgcolor="white", title="Per-analyst query time (ms) — color = status",
                          xaxis_title="ms")
        st.plotly_chart(fig, width="stretch")
    st.markdown("**Analyst findings:**")
    for r in t.get("agent_results", []):
        icon = "✅" if r.status == "ok" else "⚠️"
        st.markdown(f"{icon} **{r.agent_name}** ({r.domain}, {r.elapsed_ms} ms) — "
                    f"{r.finding if r.status == 'ok' else r.error}")
    if t.get("degraded"):
        st.warning("Degraded analysts (isolated failure; team continued, Critic excluded them): "
                   + ", ".join(f"{d['agent']} ({d['status']})" for d in t["degraded"]))
    with st.expander("Why multi-agent here — design decisions & trade-offs"):
        st.write(P.MULTI_AGENT_INTRO)
        _table(P.MULTI_AGENT_WHEN, ["Decision", "Rationale"])
        _table(P.MULTI_AGENT_TRADEOFFS, ["Trade-off accepted", "Mitigation"])


def page_demo():
    st.title("🔬 Live Demo — Governed Multi-Agent Investigation")
    st.write("Runs the real LangGraph pipeline on synthetic data. A team of specialized "
             "analysts is dispatched in parallel; results are exposed through four trace "
             "levels plus a multi-agent team view.")
    probe = llm.probe()
    st.caption(f"LLM: {probe['detail']}")

    options = (["— Conversion-drop investigation —"] + P.DEMO_QUESTIONS
               + ["— Direct analytics questions —"] + insights.questions()
               + ["— Themed reviews (health / trend / risk) —"] + themes.questions()
               + ["✍️ Custom question…"])
    choice = st.selectbox("Pick a demo question", options, index=1)
    if choice.startswith("—"):  # a group separator was selected
        choice = P.DEMO_QUESTIONS[0]
    question = st.text_input("Question", value="" if choice.startswith("✍️") else choice)
    fail_opts = {"(none)": None, "Marketing Analyst": "campaign_mix",
                 "Merchandising Analyst": "inventory_availability",
                 "Fulfillment Analyst": "fulfillment_constraints",
                 "Customer Service Analyst": "service_signal"}
    st.markdown("**Reasoning parameters** — tune these to see their impact on the answer:")
    p1, p2, p3 = st.columns(3)
    top_k = p1.selectbox("Retrieval top-k", [3, 5, 8, 10], index=1,
                         help="How many governed context chunks ChromaDB retrieves for grounding.")
    beam_width = p2.selectbox("ToT beam width", [1, 2, 3, 4], index=1,
                              help="How many primary conversion drivers the beam keeps as likely drivers.")
    depth = p3.selectbox("ToT depth", [1, 2], index=1,
                         help="Depth 2 adds sub-driver refinement; depth 1 stops at driver selection.")
    with st.expander("Advanced — resilience demo (optional)"):
        fail_label = st.selectbox("Simulate an agent failure (shows graceful degradation)",
                                  list(fail_opts), index=0)

    if not st.button("Run investigation", type="primary"):
        st.caption("Tip: try *“update the paid_social budget”* to see the read-only guardrail refuse.")
        return
    if not question.strip():
        st.warning("Enter a question first.")
        return
    with st.status("Running investigation…", expanded=False) as status:
        t = None
        for kind, payload in run_investigation_stream(
                question, inject_failure=fail_opts[fail_label],
                top_k=top_k, beam_width=beam_width, depth=depth):
            if kind == "step":
                # Show only the CURRENT step as it progresses (single updating line).
                # The full trace stays available in the Technical audit tab.
                status.update(label=f"Running… {payload['node']} — {payload['detail'][:70]}")
            else:
                t = payload
        status.update(label="Investigation complete", state="complete", expanded=False)
    if t.get("refusal"):
        st.error("🛡️ **Guardrail (read-only):** " + t["refusal"])
    tabs = st.tabs(["💬 Business answer", "👥 Multi-agent team", "📊 Evidence", "🔎 Trust details",
                    "🌳 ToT trace", "🧭 Technical audit", "📋 Action log"])
    with tabs[0]:
        _tab_business(t)
    with tabs[1]:
        _tab_team(t)
    with tabs[2]:
        _tab_evidence(t)
    with tabs[3]:
        _tab_trust(t)
    with tabs[4]:
        _tab_tot(t)
    with tabs[5]:
        _tab_audit(t)
    with tabs[6]:
        _tab_actions(t)


# ==========================================================================
# PAGE: Interactive Plan
# ==========================================================================
def page_interactive_plan():
    st.title("📄 Interactive Project Plan")
    st.caption(f"{P.SUBTITLE} · {P.TAGLINE}")
    if st.button("⬇️ Generate downloadable HTML", type="primary"):
        from build_html import render_html
        st.download_button("Download project_plan.html", data=render_html(),
                           file_name="project_plan.html", mime="text/html")
        st.success("HTML generated — click the download button above.")
    sections = [
        ("1 · Executive summary", lambda: st.write(P.EXECUTIVE_SUMMARY)),
        ("2 · Feasibility decision", lambda: st.write(P.FEASIBILITY)),
        ("3 · Business problem & users", lambda: _table(P.BUSINESS_ROLES, ["Role", "Question", "Value"])),
        ("4 · Capability roadmap", lambda: _table(P.PHASE_ROADMAP, ["Stage", "Objective", "Scope", "Success"])),
        ("5 · Tool stack", lambda: _table(P.TOOL_STACK, ["Tool", "Role", "Free?", "MVP notes"])),
        ("6 · Architecture layers", lambda: _table(P.ARCH_LAYERS, ["Layer", "Component", "Responsibility", "Control"])),
        ("7 · YAML catalog files", lambda: _table(P.YAML_FILES, ["File", "Contents", "Used by"])),
        ("9 · Knowledge graph objects", lambda: _table(P.GRAPH_OBJECTS, ["Object", "Examples", "Purpose"])),
        ("10 · Agent roles", lambda: _table(P.AGENT_ROLES, ["Role", "Purpose", "Tools", "Output"])),
        ("11 · ToT depth model", lambda: _table(P.TOT_DEPTH, ["Element", "Definition"])),
        ("12 · Source-conflict rules", lambda: _table(P.CONFLICT_RULES, ["Situation", "Decision", "Behavior"])),
        ("14 · Synthetic scenarios", lambda: _table(P.SCENARIOS, ["Scenario", "Pattern", "Evidence", "Owner"])),
        ("16 · Functional requirements", lambda: _table(P.FUNC_REQS, ["ID", "Requirement", "Priority", "Acceptance"])),
        ("17 · UI & trace levels", lambda: (_table(P.UI_SECTIONS, ["Section", "Content"]),
                                            _table(P.TRACE_LEVELS, ["Level", "Audience", "Content"]))),
        ("17.2 · Audit event schema", lambda: _table(P.AUDIT_SCHEMA, ["Field", "Example", "Purpose"])),
        ("19 · Milestones", lambda: _table(P.MILESTONES, ["Milestone", "Deliverables", "Exit criteria"])),
        ("20 · Risks", lambda: _table(P.RISKS, ["Risk", "Mitigation"])),
        ("24 · Readiness checklist", lambda: _table(P.READINESS, ["Question", "Answer"])),
    ]
    for i, (title, render) in enumerate(sections):
        with st.expander(title, expanded=(i == 0)):
            render()


# ==========================================================================
# PAGE: Diagrams
# ==========================================================================
def page_diagrams():
    from src import diagrams
    st.title("📐 Architecture, Agents & Skills")
    st.caption("Full reference architecture, agent delegation, and the flow diagrams; "
               "plus the agent and skill definitions that document the system.")

    st.header("Flow diagrams")
    for title, desc, dot in diagrams.DIAGRAMS:
        st.subheader(title)
        st.caption(desc)
        st.graphviz_chart(dot, use_container_width=True)
        st.divider()

    st.header("Agent definitions")
    st.caption("Each specialized analyst is defined as a markdown file in `agents/` with "
               "`name` / `description` / `tools` frontmatter + instructions (the "
               "`.claude/agents/<name>.md` convention). See AGENTS.md for the roster.")
    for a in agent_specs.load_specs():
        with st.expander(f"🤖 {a.get('name')} — {a.get('description', '')}"):
            tools = a.get("tools")
            tools = ", ".join(tools) if isinstance(tools, list) else (tools or "—")
            st.markdown(f"**Owner:** {a.get('owner','—')}  ·  **Domain:** {a.get('domain','—')}  "
                        f"·  **Governed driver:** `{a.get('governed_driver','—')}`  "
                        f"·  **Metric:** `{a.get('metric','—')}`")
            st.markdown(f"**Tools:** {tools}")
            tbls = a.get("tables") or []
            st.markdown("**Tables:** " + (", ".join(f"`{t}`" for t in tbls) if tbls else "—"))
            st.caption(f"`{a.get('file')}`")
            st.markdown(a.get("prompt", ""))

    st.header("Skills")
    st.caption("Reusable know-how follows the skill anatomy: a folder with `SKILL.md` "
               "(`name` + `description` frontmatter + instructions) plus optional `scripts/` "
               "and `reference/`. Only the frontmatter is always loaded — the instructions "
               "load on demand (progressive disclosure).")
    for s in agent_specs.load_skills():
        with st.expander(f"🧠 {s['name']} — {s['description']}"):
            st.code(f"{s['folder']}/\n" + "\n".join(f"  {f}" for f in s["files"]), language="text")
            st.markdown(s["instructions"])


# ==========================================================================
# PAGE: Data Catalog
# ==========================================================================
def page_catalog():
    st.title("📚 Data Catalog")
    st.caption(f"Governed source of truth · v{catalog.version()} · hash {catalog.content_hash()}")
    cat = catalog.load_catalog()
    tab1, tab2, tab3, tab4 = st.tabs(["Metrics", "Tables", "Drivers", "Lineage"])
    with tab1:
        rows = [{"metric": k, "label": m.get("label"), "domain": m.get("domain"), "owner": m.get("owner"),
                 "grain": m.get("grain"), "tables": ", ".join(m.get("approved_tables", [])),
                 "definition": (m.get("definition") or "").strip()} for k, m in cat["metrics"].items()]
        _table(rows, ["metric", "label", "domain", "owner", "grain", "tables", "definition"])
    with tab2:
        rows = [{"table": k, "grain": tb.get("grain"), "owner": tb.get("owner"),
                 "columns": ", ".join(tb.get("columns", [])),
                 "joins": ", ".join(tb.get("allowed_joins", [])),
                 "approved_use": tb.get("approved_use")} for k, tb in cat["tables"].items()]
        _table(rows, ["table", "grain", "owner", "columns", "joins", "approved_use"])
    with tab3:
        rows = [{"driver": k, "label": d.get("label"), "domain": d.get("domain"), "owner": d.get("owner"),
                 "metric": d.get("metric"), "tables": ", ".join(d.get("tables", [])),
                 "hypothesis": d.get("hypothesis")} for k, d in cat["drivers"].items()]
        _table(rows, ["driver", "label", "domain", "owner", "metric", "tables", "hypothesis"])
    with tab4:
        st.caption("metric → driver → table / system / owner (generated from YAML).")
        st.plotly_chart(_graph_figure(), width="stretch", key="catalog_graph")


# ==========================================================================
# PAGE: Evaluation
# ==========================================================================
@st.cache_data(show_spinner="Running checks…")
def _eval_results():
    from src import data_validation
    from src.workflow import classify_intent
    rows = list(data_validation.run_checks())
    # classification routing checks
    expected = ([(q, "overall" if i == 0 else "driver") for i, q in enumerate(P.DEMO_QUESTIONS[:8])]
                + [(q, "analytics") for q in insights.questions()]
                + [(q, "themed") for q in themes.questions()])
    ok = 0
    for q, exp in expected:
        got = "analytics" if insights.match(q) else "themed" if themes.match(q) else classify_intent(q)[0]
        ok += int(got == exp or (exp == "driver" and got in ("driver", "actions", "trust", "caveats")))
    rows.append({"check": "Question routing (intent classification)", "ok": ok == len(expected),
                 "detail": f"{ok}/{len(expected)} questions routed to the expected path"})
    return rows


def page_evaluation():
    st.title("🧪 Evaluation")
    st.caption("Automated checks that the synthetic data, guardrails, and routing behave as designed.")
    rows = _eval_results()
    passed = sum(r["ok"] for r in rows)
    c1, c2 = st.columns(2)
    c1.metric("Checks passed", f"{passed}/{len(rows)}")
    c2.metric("Status", "✅ All passing" if passed == len(rows) else "⚠️ Review")
    df = pd.DataFrame([{"": "✅" if r["ok"] else "⚠️", "check": r["check"], "detail": r["detail"]} for r in rows])
    st.dataframe(df, width="stretch", hide_index=True)


# ==========================================================================
# Navigation
# ==========================================================================
PAGES = {
    "🏠 Overview": page_overview,
    "✅ Feasibility Review": page_feasibility,
    "🏗️ Architecture": page_architecture,
    "📐 Architecture, Agents & Skills": page_diagrams,
    "📚 Data Catalog": page_catalog,
    "🗺️ Step-by-Step Plan": page_plan,
    "🔬 Live Demo": page_demo,
    "🧪 Evaluation": page_evaluation,
    "📄 Interactive Plan": page_interactive_plan,
}

st.sidebar.title("🛍️ Retail Analytics Assistant")
st.sidebar.caption("Governed agentic analytics · modern data platform")
selection = st.sidebar.radio("Navigate", list(PAGES.keys()))
st.sidebar.divider()
st.sidebar.markdown(f"**Catalog:** v{catalog.version()}  \n`{catalog.content_hash()}`  \n\n"
                    "**Read-only** · Faker synthetic data · free/local stack")
st.sidebar.caption("ReAct + RAG + Knowledge Graph + conditional ToT beam search. "
                   "Ollama & sentence-transformers are optional with fallbacks.")
PAGES[selection]()
