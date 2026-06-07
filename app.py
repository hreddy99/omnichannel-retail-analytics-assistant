"""
Omnichannel Retail Analytics Assistant - Streamlit app.

An interactive companion to the project plan AND a runnable prototype of the
governed investigation workflow described in Checkpoint 4.1. Six pages:
Overview, Feasibility Review, Architecture, Step-by-Step Plan, Live Demo, and
an Interactive Plan with a downloadable standalone HTML.

Run:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import catalog, graph, guardrails
from src import plan_content as P
from src.investigation import BEAM_WIDTH, QUERY_BUDGET, run_investigation

st.set_page_config(page_title="Omnichannel Retail Analytics Assistant",
                   page_icon="🛍️", layout="wide")

# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _df(rows, cols):
    return pd.DataFrame(rows, columns=cols)


def _table(rows, cols):
    st.dataframe(_df(rows, cols), width="stretch", hide_index=True)


CONF_COLOR = {
    "likely driver": "#16a34a",
    "possible contributor": "#d97706",
    "possible contributor (outside beam)": "#d97706",
    "pruned": "#dc2626",
}


# ==========================================================================
# PAGE: Overview
# ==========================================================================
def page_overview():
    st.title("🛍️ Omnichannel Retail Analytics Assistant")
    st.caption(P.SUBTITLE)
    st.success("**Feasibility decision:** " + P.FEASIBILITY)

    st.subheader("Executive summary")
    st.write(P.EXECUTIVE_SUMMARY)

    st.subheader("Business problem & intended users")
    st.write(P.BUSINESS_PROBLEM)

    st.subheader("Capstone fit & course alignment")
    _table(P.CAPSTONE_FIT, ["Capstone concept", "How the project demonstrates it", "Success measure"])

    st.subheader("Prototype status (this repository)")
    st.caption("How this runnable prototype maps to the plan. Green = built and exercised in the Live Demo.")
    status_df = _df(P.PROTOTYPE_STATUS, ["Component", "Status", "Notes"])

    def _badge(s):
        c = {"Built": "background-color:#dcfce7", "Stubbed": "background-color:#fef9c3",
             "Optional": "background-color:#e0e7ff", "Modeled": "background-color:#f1f5f9"}.get(s, "")
        return c
    st.dataframe(status_df.style.map(_badge, subset=["Status"]),
                 width="stretch", hide_index=True)


# ==========================================================================
# PAGE: Feasibility Review
# ==========================================================================
def page_feasibility():
    st.title("✅ Feasibility Review")
    st.write(
        "The plan's central feasibility claim is that the entire MVP is **free and "
        "runnable on a personal PC**. The review below assesses that claim against "
        "the proposed stack, then summarizes the project risks and their mitigations."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Required paid services", "0")
    c2.metric("External APIs to run demo", "0")
    c3.metric("Runs offline", "Yes")

    st.info(
        "**Verdict: Feasible.** Every component required to run the demo is a free, "
        "local, open-source library. This prototype confirms it: the Live Demo runs "
        "the full governed workflow (synthetic data → DuckDB evidence → conditional "
        "ToT beam search → guardrails → grounded answer) with **no external services**. "
        "The LLM (Ollama) and vector embeddings (ChromaDB) are *optional enhancements* — "
        "a deterministic stand-in is shipped so the architecture is demonstrable on any laptop."
    )

    st.subheader("Free / local tool stack")
    free_rows = [(t, r, "✅ " + f if f == "Yes" else ("🔵 " + f if f == "Optional" else f), n)
                 for (t, r, f, n) in P.TOOL_STACK]
    _table(free_rows, ["Tool", "Role", "Free / doable on PC?", "MVP notes"])

    st.subheader("What's required vs optional to run this prototype")
    a, b = st.columns(2)
    with a:
        st.markdown("**Required (all free, installed via `requirements.txt`)**")
        st.markdown("- Python, Streamlit\n- DuckDB (read-only analytics)\n- "
                    "NetworkX (knowledge graph)\n- PyYAML (governed catalog)\n- "
                    "pandas / numpy / plotly")
    with b:
        st.markdown("**Optional (documented, not needed for the demo)**")
        st.markdown("- Ollama — local LLM for planning/drafting\n- ChromaDB + "
                    "sentence-transformers — vector retrieval\n- LangGraph — "
                    "orchestration (deterministic stand-in used here)\n- CrewAI / MCP — future role separation")

    st.subheader("Risks & mitigations")
    _table(P.RISKS, ["Risk", "Mitigation"])


# ==========================================================================
# PAGE: Architecture
# ==========================================================================
def _flow_figure():
    """LangGraph-style controller flow as a left-to-right node diagram."""
    nodes = ["Question", "Classify /\nRetrieve", "Validate\nvs YAML", "Graph\nselect",
             "Conditional\nToT beam", "SQL\nvalidate", "DuckDB\nevidence",
             "Evidence\ngate / stop", "Grounded\nanswer"]
    xs = list(range(len(nodes)))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=[0] * len(nodes), mode="markers+text",
        marker=dict(size=46, color="#2563eb", line=dict(width=2, color="#1e40af")),
        text=nodes, textposition="middle center",
        textfont=dict(color="white", size=10), hoverinfo="text"))
    for i in range(len(nodes) - 1):
        fig.add_annotation(x=xs[i + 1], y=0, ax=xs[i], ay=0, xref="x", yref="y",
                           axref="x", ayref="y", showarrow=True, arrowhead=3,
                           arrowwidth=1.6, arrowcolor="#94a3b8")
    # feedback loop (revise)
    fig.add_annotation(x=2, y=0.0, ax=7, ay=0.45, xref="x", yref="y", axref="x",
                       ayref="y", showarrow=True, arrowhead=3, arrowwidth=1.3,
                       arrowcolor="#f59e0b", text="revise / retry", font=dict(size=9, color="#b45309"))
    fig.update_layout(height=230, showlegend=False, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(visible=False, range=[-0.6, len(nodes) - 0.4]),
                      yaxis=dict(visible=False, range=[-0.6, 0.7]),
                      plot_bgcolor="white")
    return fig


def _graph_figure():
    """Render the catalog-derived NetworkX graph (metric → driver → table/owner)."""
    import networkx as nx
    g = graph.build_graph()
    pos = nx.spring_layout(g, seed=7, k=0.9)
    kind_color = {"metric": "#2563eb", "driver": "#16a34a",
                  "table": "#64748b", "owner": "#d97706"}
    ex, ey = [], []
    for u, v in g.edges():
        ex += [pos[u][0], pos[v][0], None]
        ey += [pos[u][1], pos[v][1], None]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines",
                             line=dict(width=1, color="#cbd5e1"), hoverinfo="none"))
    for kind, color in kind_color.items():
        ns = [n for n in g.nodes if g.nodes[n].get("kind") == kind]
        fig.add_trace(go.Scatter(
            x=[pos[n][0] for n in ns], y=[pos[n][1] for n in ns],
            mode="markers+text", name=kind,
            marker=dict(size=18, color=color),
            text=[g.nodes[n].get("label", n) for n in ns],
            textposition="top center", textfont=dict(size=9), hoverinfo="text"))
    fig.update_layout(height=460, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(visible=False), yaxis=dict(visible=False),
                      legend=dict(orientation="h", y=1.05), plot_bgcolor="white")
    return fig


def page_architecture():
    st.title("🏗️ Updated Architecture")
    st.write(
        "Responsibilities are separated across layers. **LangGraph** is the central "
        "controller, **YAML** governs truth, **ChromaDB** retrieves context, "
        "**NetworkX** selects relationships, **DuckDB** produces evidence, and the "
        "**conditional ToT** module explores competing hypotheses only when needed. "
        "The LLM helps plan and summarize but is never a source of truth."
    )

    st.subheader("Controller flow (LangGraph state machine)")
    st.plotly_chart(_flow_figure(), width="stretch")

    st.subheader("Architecture layers")
    _table(P.ARCH_LAYERS, ["Layer", "Responsibility"])

    st.subheader("Knowledge graph generated from the YAML catalog (NetworkX)")
    st.caption(f"Live render of the catalog (v{catalog.version()}, hash {catalog.content_hash()}). "
               "Edges connect the conversion metric to its drivers, tables, and accountable owners.")
    st.plotly_chart(_graph_figure(), width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Source-conflict & priority rules")
        _table(P.CONFLICT_RULES, ["Situation", "Decision rule", "User-facing behavior"])
    with col2:
        st.subheader("ToT scoring rubric")
        rubric = [(c, f"0–{m}") for c, m in P.TOT_RUBRIC]
        rubric.append(("**Maximum total**", f"**{sum(m for _, m in P.TOT_RUBRIC)}**"))
        _table(rubric, ["Evaluation criterion", "Score"])
        st.caption(P.TOT_THRESHOLDS)


# ==========================================================================
# PAGE: Step-by-Step Plan
# ==========================================================================
def page_plan():
    st.title("🗺️ Step-by-Step Implementation Plan")

    st.subheader("Implementation milestones")
    built = {"1", "2", "3", "5", "6", "7"}  # phases substantially realized in this prototype
    rows = []
    for i, (phase, deliv, exit_c) in enumerate(P.MILESTONES, start=1):
        status = "✅ Built" if str(i) in built else ("🟡 Partial" if i == 4 else "⬜ Planned")
        rows.append((phase, deliv, exit_c, status))
    _table(rows, ["Phase", "Deliverables", "Exit criteria", "Prototype status"])
    st.caption("Phase 4 (ChromaDB vector DB) is modeled via `catalog.chunks()` with version/"
               "content_hash metadata; embeddings are optional. Phase 8 (demo polish) is this app.")

    st.subheader("Functional requirements")
    _table(P.FUNC_REQS, ["ID", "Requirement", "Acceptance criteria"])

    st.subheader("MVP demo questions")
    for i, q in enumerate(P.DEMO_QUESTIONS, 1):
        st.markdown(f"{i}. {q}")

    st.subheader("Seeded synthetic scenarios")
    _table(P.SCENARIOS, ["Seeded scenario", "Injected pattern", "Expected evidence", "Owner"])


# ==========================================================================
# PAGE: Live Demo
# ==========================================================================
def _branch_card(b):
    color = CONF_COLOR.get(b.confidence, "#64748b")
    st.markdown(
        f"<div style='border-left:5px solid {color};padding:6px 12px;margin:6px 0;"
        f"background:#f8fafc;border-radius:4px'>"
        f"<b>{b.label}</b> &nbsp;·&nbsp; score <b>{b.total}/14</b> &nbsp;·&nbsp; "
        f"<span style='color:{color}'><b>{b.confidence}</b></span><br>"
        f"<span style='font-size:0.9em;color:#475569'>{b.finding}</span></div>",
        unsafe_allow_html=True)
    with st.expander(f"Score breakdown — {b.label}"):
        sb = pd.DataFrame([{"criterion": k, "score": v} for k, v in b.scores.items()])
        st.dataframe(sb, width="stretch", hide_index=True)
        if b.sql:
            st.code(b.sql, language="sql")
        if b.evidence is not None:
            st.dataframe(b.evidence, width="stretch", hide_index=True)


def page_demo():
    st.title("🔬 Live Demo — Governed Investigation")
    st.write(
        "This runs the **actual** workflow on synthetic data: governed retrieval → "
        "read-only DuckDB evidence → conditional Tree-of-Thought beam search "
        f"(width {BEAM_WIDTH}, depth 2) → guardrails → grounded answer. "
        f"Query budget = {QUERY_BUDGET} (1 baseline + 3 driver-path + 1 follow-up)."
    )

    options = P.DEMO_QUESTIONS + ["✍️ Custom question…"]
    choice = st.selectbox("Pick a demo question", options, index=0)
    question = st.text_input("Question", value="" if choice.startswith("✍️") else choice)

    run = st.button("Run investigation", type="primary")
    if not run:
        st.caption("Tip: try a write request like *“update the paid_social budget”* to see "
                   "the read-only guardrail refuse and convert it to a recommendation.")
        return
    if not question.strip():
        st.warning("Enter a question first.")
        return

    with st.spinner("Investigating…"):
        trace = run_investigation(question)

    # Guardrail refusal (FR-09)
    if trace.get("refusal"):
        st.error("🛡️ **Guardrail (read-only):** " + trace["refusal"])

    # Headline
    a = trace["answer"]
    bl = trace["baseline"]
    st.subheader("Answer")
    st.markdown(f"### {a['headline']}")
    conf_c = "#16a34a" if a["confidence"] == "high" else "#d97706"
    st.markdown(f"**Confidence:** <span style='color:{conf_c}'>{a['confidence']}</span>",
                unsafe_allow_html=True)
    st.markdown(f"**Certified definition used:** {a['definition']}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Yesterday conversion", f"{bl['target']:.2%}")
    m2.metric("Prior 7-day avg", f"{bl['baseline']:.2%}")
    m3.metric("Change", f"{bl['pct_change']:+.1%}")
    m4.metric("Queries used", f"{trace['queries_used']}/{QUERY_BUDGET}")

    # Baseline chart
    series = bl["series"].copy()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series["date"], y=series["conversion"], mode="lines+markers",
                             name="daily conversion", line=dict(color="#2563eb")))
    fig.add_hline(y=bl["baseline"], line_dash="dash", line_color="#94a3b8",
                  annotation_text="prior 7-day avg")
    fig.add_trace(go.Scatter(x=[series["date"].iloc[-1]], y=[bl["target"]], mode="markers",
                             marker=dict(size=14, color="#dc2626"), name="yesterday"))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10),
                      yaxis_tickformat=".1%", plot_bgcolor="white",
                      title="Digital conversion: daily vs prior 7-day average")
    st.plotly_chart(fig, width="stretch")

    # Drivers
    st.markdown("#### Likely drivers (selected by beam search)")
    for d in a["drivers"]:
        c = CONF_COLOR.get(d["confidence"], "#16a34a")
        st.markdown(
            f"<div style='border-left:5px solid {c};padding:6px 12px;margin:6px 0;"
            f"background:#f0fdf4;border-radius:4px'><b>{d['label']}</b> → route to "
            f"<b>{d['owner']}</b> &nbsp;·&nbsp; <span style='color:{c}'>{d['confidence']}</span>"
            f" (score {d['score']}/14)<br><span style='font-size:0.9em;color:#475569'>"
            f"{d['finding']}</span></div>", unsafe_allow_html=True)
    if a["contributors"]:
        st.markdown("#### Possible contributors (qualified, outside the beam)")
        for d in a["contributors"]:
            st.markdown(f"- **{d['label']}** → {d['owner']} (score {d['score']}/14) — {d['finding']}")
    if a["pruned"]:
        st.markdown("#### Pruned hypotheses")
        for p in a["pruned"]:
            st.markdown(f"- ~~**{p['label']}**~~ (score {p['score']}/14) — {p['reason']}")

    st.markdown(f"**Recommendation:** {a['recommendation']}")
    with st.expander("Caveats & data-freshness limits"):
        for cv in a["caveats"]:
            st.markdown(f"- {cv}")

    # Reasoning trace
    st.divider()
    st.subheader("🧭 Reasoning trace (debug)")
    st.caption("Tools called in order — every claim is backed by a validated, read-only query.")
    for s in trace["steps"]:
        icon = "✅" if s["ok"] else "⚠️"
        st.markdown(f"{icon} **{s['node']}** — {s['detail']}")

    # ToT detail
    st.subheader("🌳 Tree-of-Thought branch scorecards")
    if trace["tot_activated"]:
        st.caption("ToT activated: multiple plausible driver paths competed.")
        for b in trace["depth1"]:
            _branch_card(b)
        if trace.get("depth2"):
            st.markdown("**Depth-2 refinement (surviving branches → sub-drivers):**")
            for d in trace["depth2"]:
                st.markdown(f"- {d['refined']}")
    else:
        st.caption("ToT not activated — a single obvious path did not require beam search.")

    with st.expander("Baseline SQL (read-only, validated)"):
        ok, reason = guardrails.check_sql(bl["sql"])
        st.code(bl["sql"], language="sql")
        st.caption(("✅ " if ok else "⚠️ ") + reason)


# ==========================================================================
# PAGE: Interactive Plan
# ==========================================================================
def page_interactive_plan():
    st.title("📄 Interactive Project Plan")
    st.caption(P.SUBTITLE)
    st.write("The full plan, section by section. Use the button to generate a standalone, "
             "shareable HTML version.")

    if st.button("⬇️ Generate downloadable HTML", type="primary"):
        from build_html import render_html
        html = render_html()
        st.download_button("Download project_plan.html", data=html,
                           file_name="project_plan.html", mime="text/html")
        st.success("HTML generated. Click the download button above.")

    with st.expander("1 · Executive summary", expanded=True):
        st.write(P.EXECUTIVE_SUMMARY)
    with st.expander("2 · Feasibility decision"):
        st.write(P.FEASIBILITY)
    with st.expander("3 · Business problem & users"):
        st.write(P.BUSINESS_PROBLEM)
    with st.expander("4 · Capstone fit"):
        _table(P.CAPSTONE_FIT, ["Concept", "Demonstration", "Success measure"])
    with st.expander("5 · Free & local tool stack"):
        _table(P.TOOL_STACK, ["Tool", "Role", "Free?", "MVP notes"])
    with st.expander("6 · Architecture layers"):
        _table(P.ARCH_LAYERS, ["Layer", "Responsibility"])
    with st.expander("7 · ToT scoring rubric"):
        _table([(c, f"0–{m}") for c, m in P.TOT_RUBRIC], ["Criterion", "Score"])
        st.caption(P.TOT_THRESHOLDS)
    with st.expander("8 · Source-conflict rules"):
        _table(P.CONFLICT_RULES, ["Situation", "Decision", "Behavior"])
    with st.expander("9 · Seeded synthetic scenarios"):
        _table(P.SCENARIOS, ["Scenario", "Pattern", "Expected evidence", "Owner"])
    with st.expander("10 · MVP demo questions"):
        for i, q in enumerate(P.DEMO_QUESTIONS, 1):
            st.markdown(f"{i}. {q}")
    with st.expander("11 · Functional requirements"):
        _table(P.FUNC_REQS, ["ID", "Requirement", "Acceptance criteria"])
    with st.expander("12 · Implementation milestones"):
        _table(P.MILESTONES, ["Phase", "Deliverables", "Exit criteria"])
    with st.expander("13 · Risks & mitigations"):
        _table(P.RISKS, ["Risk", "Mitigation"])


# ==========================================================================
# Navigation
# ==========================================================================
PAGES = {
    "🏠 Overview": page_overview,
    "✅ Feasibility Review": page_feasibility,
    "🏗️ Architecture": page_architecture,
    "🗺️ Step-by-Step Plan": page_plan,
    "🔬 Live Demo": page_demo,
    "📄 Interactive Plan": page_interactive_plan,
}

st.sidebar.title("🛍️ Retail Analytics Assistant")
st.sidebar.caption("Governed investigation workflow · Checkpoint 4.1")
selection = st.sidebar.radio("Navigate", list(PAGES.keys()))
st.sidebar.divider()
st.sidebar.markdown(
    f"**Catalog:** v{catalog.version()}  \n`{catalog.content_hash()}`  \n\n"
    "**Read-only** · synthetic data · free/local stack")
st.sidebar.caption("LLM (Ollama) & ChromaDB embeddings are optional; the demo runs "
                   "with a deterministic stand-in and no external services.")

PAGES[selection]()
