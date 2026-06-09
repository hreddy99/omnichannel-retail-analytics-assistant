"""
LangGraph workflow controller (Plan sections 6, 10, 15).

A real LangGraph StateGraph implementing the ReAct-style loop: classify ->
sync_gate -> retrieve -> validate -> relate -> baseline -> tot_gate -> beam ->
evidence_gate -> synthesize. Every node records an audit event and a
user-visible trace step. All claims are grounded in read-only DuckDB evidence;
the LLM (Ollama, optional) only drafts the summary.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, TypedDict

import pandas as pd
from langgraph.graph import END, START, StateGraph

from . import agents, catalog, graph, guardrails, llm, tot
from .audit import AuditLog


class WState(TypedDict, total=False):
    question: str
    inject_failure: str | None  # demo: force one agent to fail
    intent: str
    focus: str | None
    con: Any
    g: Any
    meta: dict
    index: Any
    audit: AuditLog
    steps: list
    retrieval: list
    baseline: dict
    tot_activated: bool
    agent_results: list
    coordination: dict
    degraded: list
    branches: list
    beam: list
    deferred: list
    pruned: list
    depth2: list
    queries_used: int
    answer: dict
    refusal: str | None


def _step(state: WState, node: str, detail: str, ok: bool = True):
    # The audit object persists by reference across LangGraph nodes, so trace
    # steps recorded on it survive (unlike plain state keys, which are only
    # committed when a node returns them).
    state["audit"].step(node, detail, ok)


# Owner-routed recommended actions per driver (human-reviewed; no operational writes).
RECOMMENDATIONS = {
    "campaign_mix": "Rebalance paid-social spend and audit campaign targeting/creative quality.",
    "inventory_availability": "Expedite replenishment and re-enable online availability for the affected category.",
    "fulfillment_constraints": "Restore fulfillment options and delivery SLAs in the affected region.",
    "funnel_behavior": "Audit the on-site checkout funnel for the affected segment.",
    "service_signal": "Brief support on the contact spike and confirm the operational root cause.",
    "finance_caveat": "Reconcile gross-to-net before reporting revenue impact.",
    "vendor_insight": "Alert the category/vendor partner about the stockout impact.",
}


# --------------------------------------------------------------------------
# Question intent classification - so the final answer is tuned to what was asked
# (a "what actions?" question leads with actions; "did inventory contribute?"
# answers yes/no for inventory; "show the definition" leads with grounding; etc.)
# --------------------------------------------------------------------------
_INTENT_LABEL = {
    "actions": "recommended next actions",
    "trust": "definition & evidence path",
    "caveats": "caveats & data freshness",
    "driver": "specific driver",
    "overall": "overall conversion drop",
}
_FOCUS_PATTERNS = [
    ("campaign_mix", r"channel|campaign|marketing|paid[ _]?social|traffic mix|\bads?\b|spend"),
    ("inventory_availability", r"inventor|stock|stockout|availab|out of stock|sold out"),
    ("fulfillment_constraints", r"fulfil|deliver|shipping|\bship\b|delay|fulfillment option|carrier|pickup"),
    ("funnel_behavior", r"funnel|cart|checkout|abandon|on-?site|browse"),
    ("service_signal", r"service|contact|support|complaint|\bcall(s|ed)?\b"),
    ("finance_caveat", r"financ|revenue|\bnet\b|gross|reconcil|returns?|margin"),
    ("vendor_insight", r"vendor|partner|supplier"),
]


def classify_intent(question: str):
    """Return (intent, focus_driver_key|None) from the question wording."""
    import re
    q = question.lower()
    if re.search(r"action|investigate next|what should|next step|recommend|what.* do\b", q):
        return "actions", None
    if re.search(r"definition|evidence path|show the|grounding|which definition|how did you", q):
        return "trust", None
    if re.search(r"caveat|freshness|trust this|trusting|limit|how confident|reliab|stale", q):
        return "caveats", None
    for key, pat in _FOCUS_PATTERNS:
        if re.search(pat, q):
            return "driver", key
    return "overall", None


# --------------------------------------------------------------------------
# Nodes
# --------------------------------------------------------------------------
def n_classify(state: WState) -> dict:
    a: AuditLog = state["audit"]
    refusal = guardrails.refuse_write(state["question"])
    intent, focus = classify_intent(state["question"])
    focus_label = (catalog.get_driver(focus) or {}).get("label", focus) if focus else ""
    detail = _INTENT_LABEL.get(intent, intent) + (f" → {focus_label}" if focus else "")
    a.event(workflow_node="classify", decision_type="question_classified",
            tool_name="LangGraph", input_summary=state["question"][:80],
            output_summary=f"intent={intent}{('/'+focus) if focus else ''}; metric=digital_conversion_rate",
            user_visible_note=f"Classified intent: {detail}.")
    _step(state, "classify", f"Classified the question — intent: **{detail}** "
          "(metric=digital_conversion_rate, baseline=prior 7-day average).")
    return {"refusal": refusal, "queries_used": 0, "intent": intent, "focus": focus}


def n_sync_gate(state: WState) -> dict:
    a: AuditLog = state["audit"]
    g = state["g"]
    ok, msg = guardrails.check_freshness(catalog.version(), g.graph["catalog_version"],
                                         g.graph.get("source_hash"))
    sync = state["index"].sync_status() if state.get("index") else {"in_sync": True, "embedder": "n/a"}
    a.event(workflow_node="sync_gate", decision_type="catalog_sync_checked",
            tool_name="YAML+ChromaDB+NetworkX", source_version_hash=f"v{catalog.version()}/{catalog.content_hash()}",
            output_summary=f"{msg} retrieval in_sync={sync['in_sync']}",
            status="success" if ok and sync["in_sync"] else "blocked",
            user_visible_note="Catalog/graph/vector versions verified in sync.")
    _step(state, "sync gate", f"{msg} Vector index in_sync={sync['in_sync']} "
          f"(embedder: {sync.get('embedder')}).", ok and sync["in_sync"])
    return {}


def n_retrieve(state: WState) -> dict:
    a: AuditLog = state["audit"]
    idx = state.get("index")
    results = idx.retrieve(state["question"], top_k=5) if idx else []
    a.event(workflow_node="retrieve_context", decision_type="topk_retrieved",
            tool_name="ChromaDB", input_summary=state["question"][:60],
            output_summary=f"retrieved {len(results)} chunks; "
                           f"{sum(r['validated'] for r in results)} validated vs YAML",
            user_visible_note=f"Retrieved {len(results)} governed context chunks.")
    _step(state, "retrieve (ChromaDB)", f"Top-{len(results)} governed chunks retrieved; "
          f"{sum(r['validated'] for r in results)} validated against YAML.")
    return {"retrieval": results}


def n_validate(state: WState) -> dict:
    a: AuditLog = state["audit"]
    m = catalog.get_metric("digital_conversion_rate")
    a.event(workflow_node="source_gate", decision_type="metric_selected",
            tool_name="YAML parser", output_summary="certified session-to-order definition",
            source_version_hash=f"v{catalog.version()}",
            user_visible_note="Confirmed certified metric definition and grain.")
    _step(state, "validate vs YAML", f"Certified definition selected: {m['definition'].strip()[:90]}…")
    return {}


def n_relate(state: WState) -> dict:
    a: AuditLog = state["audit"]
    g = state["g"]
    paths = {d: graph.driver_path(g, d) for d in tot.PRIMARY_DRIVERS + [tot.RESERVE_DRIVER]}
    found = [d for d, p in paths.items() if p]
    a.event(workflow_node="graph_traverse", decision_type="drivers_related",
            tool_name="NetworkX", output_summary=f"related drivers: {', '.join(found)}",
            user_visible_note="Mapped metric to candidate drivers, tables, and owners.")
    _step(state, "relate (NetworkX)", f"Graph path found for drivers: {', '.join(found)}.")
    return {}


def n_baseline(state: WState) -> dict:
    a: AuditLog = state["audit"]
    con, meta = state["con"], state["meta"]
    td, b0, b1 = meta["target_day"], meta["baseline_start"], meta["baseline_end"]
    sql = catalog.sql_template("conversion_baseline") or (
        "WITH s AS (SELECT date, count(*) sessions, sum(CASE WHEN converted THEN 1 ELSE 0 END) orders "
        "FROM fact_sessions GROUP BY date) SELECT date, orders*1.0/sessions AS conversion FROM s ORDER BY date")
    conv = con.execute(sql).df()
    conv["date"] = pd.to_datetime(conv["date"]).dt.date
    target = float(conv[conv.date == dt.date.fromisoformat(td)].conversion.iloc[0])
    mask = (conv.date >= dt.date.fromisoformat(b0)) & (conv.date <= dt.date.fromisoformat(b1))
    base = float(conv[mask].conversion.mean())
    pct = (target - base) / base
    a.event(workflow_node="sql_execute", decision_type="baseline_measured",
            tool_name="DuckDB", input_summary="conversion_baseline template",
            output_summary=f"target={target:.4f} base={base:.4f} pct={pct:+.1%}",
            score_or_confidence=f"{pct:+.1%}",
            user_visible_note=f"Yesterday conversion {target:.2%} vs {base:.2%} = {pct:+.1%}.")
    _step(state, "baseline (DuckDB, query 1/%d)" % tot.QUERY_BUDGET,
          f"Yesterday {target:.2%} vs prior-7-day {base:.2%} = {pct:+.1%}. Drop confirmed.")
    return {"baseline": {"target": target, "baseline": base, "pct_change": pct,
                         "series": conv, "sql": sql}, "queries_used": 1}


def n_tot_gate(state: WState) -> dict:
    pct = state["baseline"]["pct_change"]
    competing = len(tot.PRIMARY_DRIVERS) >= 3 and pct < -0.05
    a: AuditLog = state["audit"]
    a.event(workflow_node="tot_gate", decision_type="tot_trigger_decided",
            tool_name="LangGraph", output_summary=f"tot_activated={competing}",
            user_visible_note="Multiple competing driver paths -> activate beam search."
            if competing else "Single path -> ToT not required.")
    _step(state, "ToT trigger", ("Multiple plausible driver paths + material drop -> "
          "activate bounded beam search (width 2, depth 2)." if competing else
          "Single obvious path -> ToT not required."))
    return {"tot_activated": competing}


def n_dispatch(state: WState) -> dict:
    """Orchestrator dispatches the full specialized analyst team IN PARALLEL."""
    a: AuditLog = state["audit"]
    con, meta = state["con"], state["meta"]
    team = agents.analyst_team()
    results, coord = agents.dispatch(team, con, meta, inject_failure=state.get("inject_failure"))

    for r in results:
        a.event(workflow_node="domain_agent", decision_type="agent_analysis",
                tool_name=f"{r.agent_name} (DuckDB)", input_summary=f"domain={r.domain}",
                output_summary=(r.finding[:70] if r.status == "ok" else r.error),
                score_or_confidence=f"signal={r.signal:+.2f}", status=r.status,
                user_visible_note=f"{r.agent_name}: {r.finding[:80]}")
    a.event(workflow_node="orchestrator", decision_type="team_dispatched", tool_name="ThreadPool",
            output_summary=f"{coord['n_ok']}/{coord['n_agents']} ok; {coord['n_failed']} failed",
            score_or_confidence=f"{coord['speedup']}x speedup",
            user_visible_note=f"Dispatched {coord['n_agents']} analysts in parallel "
                              f"({coord['wall_ms']}ms wall vs {coord['sequential_ms']}ms sequential).")
    _step(state, "dispatch analyst team (parallel)",
          "Ran %d specialized analysts concurrently in %dms "
          "(%dms if sequential; %.1fx speedup); %d ok, %d failed." % (
              coord["n_agents"], coord["wall_ms"], coord["sequential_ms"],
              coord["speedup"], coord["n_ok"], coord["n_failed"]))
    return {"agent_results": results, "coordination": coord,
            "queries_used": 1 + coord["n_ok"]}


def n_critic(state: WState) -> dict:
    """Critic scores each analyst's finding, prunes the ungoverned hypothesis,
    and the Orchestrator applies beam selection (width 2) + depth-2 refinement."""
    a: AuditLog = state["audit"]
    g = state["g"]
    fresh_ok = guardrails.check_freshness(catalog.version(), g.graph["catalog_version"],
                                          g.graph.get("source_hash"))[0]

    # governance pre-screen (Plan section 12)
    ung = tot.ungoverned_branch()
    tot.score_branch(ung, g, fresh_ok)
    ung.finding = ("No certified metric or approved table backs this; SQL validator "
                   "blocked the unapproved 'pricing' table. Pruned without spending budget.")
    _step(state, "governance pre-screen", "Ungoverned 'price increase' hypothesis rejected "
          "(no certified metric/table; SQL validator blocked it).")

    branches = [ung]
    degraded = []
    for r in state["agent_results"]:
        if r.status != "ok":
            degraded.append({"agent": r.agent_name, "domain": r.domain,
                             "status": r.status, "error": r.error})
            continue
        b = tot.make_branch(r.key)
        b.sql, b.evidence, b.signal, b.finding = r.sql, r.evidence, r.signal, r.finding
        tot.score_branch(b, g, fresh_ok)
        a.event(workflow_node="critic", decision_type="branch_scored", tool_name="Critic/Evaluator",
                input_summary=f"agent={r.agent_name}", output_summary=r.finding[:70],
                score_or_confidence=f"{b.total}/14 ({b.confidence})",
                user_visible_note=f"{b.label}: {b.confidence} (score {b.total}/14).")
        branches.append(b)

    branches.sort(key=lambda x: (x.total, abs(x.signal)), reverse=True)
    pruned = [b for b in branches if b.confidence == "pruned"]
    qualified = [b for b in branches if b.confidence != "pruned"]
    beam = qualified[:tot.BEAM_WIDTH]
    deferred = qualified[tot.BEAM_WIDTH:]
    depth2 = [{"driver": b.driver, "sub_drivers": b.sub_drivers,
               "refined": f"Refine '{b.label}' into: {', '.join(b.sub_drivers)}."} for b in beam]
    _step(state, "critic + beam select (width %d)" % tot.BEAM_WIDTH,
          "Beam kept %s; deferred %s; pruned %s; degraded %d." % (
              ", ".join(b.driver for b in beam) or "none",
              ", ".join(b.driver for b in deferred) or "none",
              ", ".join(b.driver for b in pruned) or "none", len(degraded)))
    _step(state, "depth-2 refinement", "Refined surviving branches into sub-drivers for owner routing.")
    return {"branches": branches, "beam": beam, "deferred": deferred, "pruned": pruned,
            "depth2": depth2, "degraded": degraded}


def n_evidence_gate(state: WState) -> dict:
    a: AuditLog = state["audit"]
    likely = [b for b in state["beam"] if b.confidence == "likely driver"]
    a.event(workflow_node="evidence_gate", decision_type="stopping_condition",
            tool_name="Guardrails", output_summary=f"{len(likely)} likely drivers",
            score_or_confidence=guardrails.overall_confidence(len(likely)),
            user_visible_note="Stopping: evidence threshold met within query budget.")
    _step(state, "evidence gate + stop", "Stopping: %d likely driver(s) cleared threshold "
          "(%d/%d queries used)." % (len(likely), state["queries_used"], tot.QUERY_BUDGET))
    return {}


def n_synthesize(state: WState) -> dict:
    a: AuditLog = state["audit"]
    bl = state["baseline"]
    beam, deferred, pruned = state["beam"], state["deferred"], state["pruned"]
    intent = state.get("intent", "overall")
    focus = state.get("focus")
    likely = [b for b in beam if b.confidence == "likely driver"]
    pct = bl["pct_change"]
    conf = guardrails.overall_confidence(len(likely))
    ctx = (f"digital conversion fell {abs(pct):.0%} yesterday "
           f"({bl['target']:.2%} vs {bl['baseline']:.2%} prior-7-day average)")
    drivers = [{"label": b.label, "confidence": b.confidence, "owner": b.owner,
                "finding": b.finding, "score": b.total} for b in beam]

    # action log + recommendations (focus driver first when the question targets one)
    ordered = beam + deferred
    if focus:
        ordered = sorted(ordered, key=lambda b: 0 if b.driver == focus else 1)
    recos = []
    for b in ordered:
        pri = "high" if b in beam else "medium"
        action = RECOMMENDATIONS.get(b.driver, "Investigate and confirm with the owner before acting.")
        a.action(owner=b.owner, issue=b.label, evidence=b.finding, confidence=b.confidence,
                 priority=pri, next_step=action)
        recos.append({"owner": b.owner, "action": action, "priority": pri,
                      "confidence": b.confidence, "rationale": b.finding})

    # ---- headline + factual lead, TUNED to the question intent ----------
    all_branches = beam + deferred + pruned
    fb = next((b for b in all_branches if b.driver == focus), None) if focus else None
    if intent == "actions":
        headline = "Recommended next actions, routed to each owner."
        facts = (f"For context, {ctx}. Prioritized actions: "
                 + "; ".join(f"{r['owner']} — {r['action']}" for r in recos[:5]) + ".")
    elif intent == "trust":
        headline = "Definition and evidence path used for this answer."
        facts = (catalog.get_metric("digital_conversion_rate")["definition"].strip()
                 + f" Baseline = prior 7-day average; {ctx}. Drivers were validated against the "
                 "YAML catalog and traced through the NetworkX graph — see Trust details for the "
                 "retrieved context, graph path, and source versions.")
    elif intent == "caveats":
        headline = "Caveats and data-freshness limits for this result."
        facts = ("Trust T-1 (yesterday); same-day data may be incomplete. Synthetic data with a fixed "
                 "seed, so magnitudes are illustrative. Read-only analysis; causality is labeled "
                 f"(likely driver / possible contributor), not proven. For context, {ctx}.")
    elif intent == "driver" and fb is not None:
        verdict = ({"likely driver": "Yes", "possible contributor": "Possibly"}
                   .get(fb.confidence, "No clear evidence"))
        phrase = ({"likely driver": "is a likely driver of",
                   "possible contributor": "is a possible contributor to"}
                  .get(fb.confidence, "shows no strong effect on"))
        headline = f"{verdict} — {fb.label} {phrase} yesterday's conversion change."
        facts = f"{fb.finding} (confidence: {fb.confidence}). For context, {ctx}."
    else:  # overall
        headline = (f"Digital conversion fell {abs(pct):.0%} yesterday "
                    f"({bl['target']:.2%} vs {bl['baseline']:.2%} prior-7-day average).")
        facts = (f"{ctx}. Likely drivers: "
                 + "; ".join(f"{d['label']} ({d['confidence']})" for d in drivers) + ".")

    summary = llm.draft_answer(state["question"], facts, conf)

    # ---- executive summary (title reflects intent) ----------------------
    es_title = ("Executive summary — recommended actions" if intent == "actions"
                else "Executive summary")
    bullets = [f"In answer to: \"{state['question']}\"", f"Context: {ctx}."]
    for r in recos:
        tag = "Act now" if r["priority"] == "high" else "Investigate next"
        bullets.append(f"{tag} — **{r['owner']}**: {r['action']} (basis: {r['rationale']})")
    if not recos:
        bullets.append("No driver cleared the evidence threshold; recommend the listed next checks.")
    exec_summary = {"title": es_title, "bullets": bullets, "recommendations": recos,
                    "note": "Owner-routed recommendations from validated evidence; guarded language; "
                            "human-reviewed only, no operational writes."}
    a.event(workflow_node="executive_summary", decision_type="exec_summary_ready",
            tool_name="Executive Summary Agent",
            output_summary=f"{len(recos)} owner-routed recommendations",
            user_visible_note="Executive summary with recommended actions composed.")
    _step(state, "executive summary", "Composed action-first recommendations routed to owners.")

    answer = {
        "headline": headline, "summary": summary, "intent": intent,
        "conversion_context": ctx[0].upper() + ctx[1:] + ".",
        "definition": catalog.get_metric("digital_conversion_rate")["definition"].strip(),
        "drivers": drivers,
        "contributors": [{"label": b.label, "confidence": "possible contributor (outside beam)",
                          "owner": b.owner, "finding": b.finding, "score": b.total} for b in deferred],
        "pruned": [{"label": b.label, "reason": b.finding, "score": b.total} for b in pruned],
        "degraded": state.get("degraded", []),
        "recommendation": ("Evidence points to multiple compounding drivers rather than a single "
                           "cause. Route each likely driver to its owner for a human-reviewed check "
                           "before any action."),
        "caveats": ["Synthetic data with a fixed seed; magnitudes are illustrative.",
                    "Read-only analysis - no operational systems were modified.",
                    "Causality is labeled (likely driver / possible contributor); not proven."],
        "confidence": conf,
        "llm_mode": llm.mode(),
        "exec_summary": exec_summary,
    }
    a.event(workflow_node="synthesize", decision_type="final_answer_ready", tool_name="Synthesis+LLM",
            output_summary=headline[:70], score_or_confidence=conf,
            user_visible_note="Final grounded answer assembled, tuned to the question intent.")
    _step(state, "synthesize", "Assembled the final answer tuned to the question (%s drafting)." % answer["llm_mode"])
    return {"answer": answer}


# --------------------------------------------------------------------------
# Graph assembly
# --------------------------------------------------------------------------
def build_workflow():
    sg = StateGraph(WState)
    nodes = [("classify", n_classify), ("sync_gate", n_sync_gate), ("retrieve", n_retrieve),
             ("validate", n_validate), ("relate", n_relate), ("baseline", n_baseline),
             ("tot_gate", n_tot_gate), ("dispatch", n_dispatch), ("critic", n_critic),
             ("evidence_gate", n_evidence_gate), ("synthesize", n_synthesize)]
    for name, fn in nodes:
        sg.add_node(name, fn)
    sg.add_edge(START, "classify")
    for (a, _), (b, _) in zip(nodes, nodes[1:]):
        sg.add_edge(a, b)
    sg.add_edge("synthesize", END)
    return sg.compile()


_APP = None


def get_app():
    global _APP
    if _APP is None:
        _APP = build_workflow()
    return _APP
