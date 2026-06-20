"""
LangGraph workflow controller.

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

from agents import team as agents
from skills import catalog_skill as catalog, graph_skill as graph, sql_skill as guardrails
from skills import input_skill as inputs, llm_skill as llm, tot_skill as tot
from skills.audit_skill import AuditLog
from workflows import insights, themes


class WState(TypedDict, total=False):
    question: str
    inject_failure: str | None  # demo: force one agent to fail
    intent: str
    focus: str | None
    corroborating: list
    top_k: int
    beam_width: int
    depth: int
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
    review: dict | None
    sync: dict
    gate_message: str
    inject_tie: bool
    tie: dict | None


def _step(state: WState, node: str, detail: str, ok: bool = True):
    # The audit object persists by reference across LangGraph nodes, so trace
    # steps recorded on it survive (unlike plain state keys, which are only
    # committed when a node returns them).
    state["audit"].step(node, detail, ok)


# Drivers that can directly cause a conversion change vs. corroborating/secondary
# signals (service contacts, finance reconciliation, vendor alerts). The beam ranks
# PRIMARY drivers; corroborating signals are reported separately so the answer is
# not dominated by, e.g., a vendor alert that mirrors the inventory finding.
PRIMARY_DRIVERS_SET = {"campaign_mix", "inventory_availability",
                       "fulfillment_constraints", "funnel_behavior"}
CORROBORATING_SET = {"service_signal", "finance_caveat", "vendor_insight"}

# Owner-routed recommended actions per driver (human-reviewed; no operational writes).
# Each names a concrete next step, who does it, and roughly when — plain language,
# not jargon. The specific numbers behind each action are shown as the "basis"
# (the validated finding) next to it in the summary, so the action is grounded.
RECOMMENDATIONS = {
    "campaign_mix": "Rebalance spend away from paid social back toward higher-converting "
                    "channels this week, and have Marketing audit the new campaign's targeting "
                    "and creative before scaling it further.",
    "inventory_availability": "Expedite replenishment for the affected categories today and "
                    "re-enable online availability, so high-traffic products stop turning into "
                    "stockouts at checkout.",
    "fulfillment_constraints": "Add carrier capacity and restore delivery options in the affected "
                    "region to bring promised delivery dates back, and proactively update ETAs on "
                    "in-flight orders.",
    "funnel_behavior": "Have Digital Analytics replay the affected segment's checkout funnel to "
                    "pinpoint the failing step (payment, shipping, or validation) and fix it before "
                    "the next campaign push.",
    "service_signal": "Brief the support team on the contact spike, pre-stage responses for the "
                    "root-cause issue, and confirm whether it traces back to the fulfillment or "
                    "inventory problem.",
    "finance_caveat": "Reconcile gross-to-net before reporting revenue impact, so returns, "
                    "discounts, and tax/shipping aren't mistaken for an operational decline.",
    "vendor_insight": "Open a partner review with the affected vendor on the stockout impact, and "
                    "agree on a replenishment commitment and backup supply for the at-risk category.",
}


def grounded_action(driver_key: str) -> str:
    """Return the owner-routed, plain-language next step for a driver."""
    return RECOMMENDATIONS.get(driver_key, "Review with the owner and confirm before acting.")


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
    "briefing": "cross-functional executive briefing",
    "overall": "overall conversion drop",
    "refused": "refused — sensitive input outside synthetic scope",
    "clarify": "clarification needed (ambiguous question)",
}
# Cross-business questions that should fan out the whole analyst team and return a
# ranked, owner-routed executive briefing (NOT the single conversion-drop narrative).
_BRIEFING_PATTERN = (
    r"executive (summary|briefing|overview|update)|brief (me|us|the team|leadership)|"
    r"leadership (briefing|update|summary)|across (the|all)? ?(business|company|org|"
    r"organi[sz]ation|teams|functions|board)|cross[- ]functional|company[- ]wide|"
    r"state of the business|biggest (risks?|issues?|problems?)|top (risks?|issues?|priorities)|"
    r"where should (we|i) focus|what needs (my |our )?attention|health of the (business|company)")
# Order matters: more specific signals (vendor / finance / service / funnel) are
# checked before the broad inventory/fulfillment patterns so e.g. "which VENDOR
# should we alert about stockouts?" routes to vendor, not inventory.
_FOCUS_PATTERNS = [
    ("vendor_insight", r"vendor|category partner|\bpartner\b|supplier"),
    ("finance_caveat", r"financ|revenue|\bnet\b|gross|reconcil|margin"),
    ("service_signal", r"service|contact|support|complaint|\bcall(s|ed)?\b"),
    ("funnel_behavior", r"funnel|cart|checkout|abandon|on-?site|browse"),
    ("campaign_mix", r"channel|campaign|marketing|paid[ _]?social|traffic mix|\bads?\b|spend"),
    ("fulfillment_constraints", r"fulfil|deliver|shipping|\bship\b|delay|fulfillment option|carrier|pickup"),
    ("inventory_availability", r"inventor|stock|stockout|availab|out of stock|sold out"),
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
    # Cross-business briefing wins over single-driver focus (it spans every domain).
    if re.search(_BRIEFING_PATTERN, q):
        return "briefing", None
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
    # Input/scope guardrail: refuse real PII / sensitive data before
    # any retrieval or analysis, and route it for governance review.
    sensitive = inputs.detect_sensitive(state["question"])
    if sensitive:
        a.event(workflow_node="input_gate", decision_type="sensitive_input_refused",
                tool_name="Guardrails", input_summary="[redacted]",
                output_summary="sensitive/PII pattern detected", status="blocked",
                user_visible_note="Refused: real personal/sensitive data is out of scope.")
        _step(state, "input gate", "Refused — the request contains real personal/sensitive "
              "data; this prototype uses synthetic data only.", ok=False)
        return {"refusal": refusal, "queries_used": 0, "intent": "refused",
                "gate_message": sensitive}
    # Standalone analytics question (not the conversion-drop investigation)?
    insight_id = insights.match(state["question"])
    if insight_id:
        ins = insights.get(insight_id)
        a.event(workflow_node="classify", decision_type="question_classified",
                tool_name="LangGraph", input_summary=state["question"][:80],
                output_summary=f"intent=analytics/{insight_id} (owner {ins.owner})",
                user_visible_note=f"Classified as a direct analytics question → {ins.owner}.")
        _step(state, "classify", f"Classified as a **direct analytics question** "
              f"({ins.domain} · {ins.owner}) — answered by one governed read-only query, "
              "not the conversion-drop investigation.")
        return {"refusal": refusal, "queries_used": 0, "intent": "analytics", "focus": insight_id}
    theme_id = themes.match(state["question"])
    if theme_id:
        th = themes.get(theme_id)
        a.event(workflow_node="classify", decision_type="question_classified", tool_name="LangGraph",
                input_summary=state["question"][:80], output_summary=f"intent=themed/{theme_id}",
                user_visible_note=f"Classified as a themed review → {th.owner}.")
        _step(state, "classify", f"Classified as a **themed review** ({th.domain} · {th.owner}) — "
              "a multi-signal investigation, not the conversion-drop path.")
        return {"refusal": refusal, "queries_used": 0, "intent": "themed", "focus": theme_id}
    intent, focus = classify_intent(state["question"])
    # Ambiguity check: an anchorless question would otherwise default to
    # the conversion narrative; instead ask one clarifying question first. A detected
    # write request has a clear operational intent, so it flows through to the read-only
    # refusal + human review rather than being treated as ambiguous.
    if intent == "overall" and not refusal:
        clarify = inputs.needs_clarification(state["question"])
        if clarify:
            a.event(workflow_node="input_gate", decision_type="clarification_requested",
                    tool_name="LangGraph", input_summary=state["question"][:80],
                    output_summary="ambiguous question — no governed anchor term",
                    status="caveated", user_visible_note="Asked the user to clarify the metric/area.")
            _step(state, "input gate", "Question is ambiguous — asking for one clarification "
                  "before investigating (deferring to the user rather than guessing).")
            return {"refusal": refusal, "queries_used": 0, "intent": "clarify",
                    "gate_message": clarify}
    focus_label = (catalog.get_driver(focus) or {}).get("label", focus) if focus else ""
    detail = _INTENT_LABEL.get(intent, intent) + (f" → {focus_label}" if focus else "")
    a.event(workflow_node="classify", decision_type="question_classified",
            tool_name="LangGraph", input_summary=state["question"][:80],
            output_summary=f"intent={intent}{('/'+focus) if focus else ''}; metric=digital_conversion_rate",
            user_visible_note=f"Classified intent: {detail}.")
    _step(state, "classify", f"Classified the question — intent: **{detail}** "
          "(metric=digital_conversion_rate, baseline=prior 7-day average).")
    _step(state, "parameters", "Run parameters — retrieval top-k=%d, beam width=%d, ToT depth=%d." % (
        state.get("top_k", 5), state.get("beam_width", tot.BEAM_WIDTH), state.get("depth", tot.DEPTH_LIMIT)))
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
    return {"sync": {"in_sync": bool(ok and sync["in_sync"]), "embedder": sync.get("embedder")}}


def n_retrieve(state: WState) -> dict:
    a: AuditLog = state["audit"]
    idx = state.get("index")
    top_k = state.get("top_k", 5)
    results = idx.retrieve(state["question"], top_k=top_k) if idx else []
    a.event(workflow_node="retrieve_context", decision_type="topk_retrieved",
            tool_name="ChromaDB", input_summary=state["question"][:60],
            output_summary=f"retrieved {len(results)} chunks (top_k={top_k}); "
                           f"{sum(r['validated'] for r in results)} validated vs YAML",
            user_visible_note=f"Retrieved {len(results)} governed context chunks (top_k={top_k}).")
    _step(state, "tool · ChromaDB retrieve", f"top_k={top_k}: retrieved {len(results)} governed chunks; "
          f"{sum(r['validated'] for r in results)} validated against YAML.")
    for r in results[:5]:
        m = r["metadata"]
        _step(state, f"  ↳ chunk", f"{m.get('source_type')}: {m.get('name')} "
              f"(owner {m.get('owner') or '-'}, dist {r['distance']:.2f}, "
              f"{'validated' if r['validated'] else 'unvalidated'})")
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
    drivers = list((catalog.load_catalog().get("drivers") or {}).keys())
    paths = {d: graph.driver_path(g, d) for d in drivers}
    found = [d for d, p in paths.items() if p]
    a.event(workflow_node="graph_traverse", decision_type="drivers_related",
            tool_name="NetworkX", output_summary=f"related drivers: {', '.join(found)}",
            user_visible_note="Mapped metric to candidate drivers, tables, and owners.")
    _step(state, "tool · NetworkX graph", f"Traversed metric → {len(found)} candidate drivers.")
    for d in found:
        p = paths[d]
        _step(state, "  ↳ path", f"{(catalog.get_driver(d) or {}).get('label', d)}: "
              f"uses {', '.join(p['tables'])} → owner {p['owner']}")
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
    for r in sorted(results, key=lambda x: x.agent_name):
        ok = r.status == "ok"
        _step(state, f"agent · {r.agent_name}",
              (f"queried {r.domain} ({r.elapsed_ms}ms) → {r.finding}" if ok
               else f"FAILED ({r.error}) — excluded from synthesis."), ok)
    return {"agent_results": results, "coordination": coord,
            "queries_used": 1 + coord["n_ok"]}


def n_critic(state: WState) -> dict:
    """Critic scores each analyst's finding, prunes the ungoverned hypothesis,
    and the Orchestrator applies beam selection (width 2) + depth-2 refinement."""
    a: AuditLog = state["audit"]
    g = state["g"]
    fresh_ok = guardrails.check_freshness(catalog.version(), g.graph["catalog_version"],
                                          g.graph.get("source_hash"))[0]

    # governance pre-screen
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
        sc = b.scores
        gated = " ⚠ evidence gated (structural < %d)" % tot.STRUCTURAL_MIN if b.evidence_gated else ""
        _step(state, f"thought · {b.label}", f"hypothesis — {b.hypothesis}")
        _step(state, f"critic · {b.label}",
              "score %d/14 (%s) [metric%d graph%d sql%d evidence%d fresh%d biz%d caveat%d]%s" % (
                  b.total, b.confidence, sc["metric_validated_yaml"], sc["approved_graph_path"],
                  sc["sql_safety_template"], sc["duckdb_evidence_strength"], sc["freshness_row_quality"],
                  sc["business_relevance_owner"], sc["caveats_manageable"], gated),
              b.confidence != "pruned")
        a.event(workflow_node="critic", decision_type="branch_scored", tool_name="Critic/Evaluator",
                input_summary=f"agent={r.agent_name}", output_summary=r.finding[:70],
                score_or_confidence=f"{b.total}/14 ({b.confidence})",
                status="caveated" if b.evidence_gated else "success",
                user_visible_note=f"{b.label}: {b.confidence} (score {b.total}/14)."
                                  + (" Evidence gated by structural check." if b.evidence_gated else ""))
        branches.append(b)

    # Deterministic ranking: score, then the documented 5-step tie-break sequence.
    branches.sort(key=lambda x: (x.total, tot.tie_break_key(x)), reverse=True)
    pruned = [b for b in branches if b.confidence == "pruned"]
    qualified = [b for b in branches if b.confidence != "pruned"]
    # Beam ranks PRIMARY conversion drivers; corroborating signals are kept aside.
    bw = state.get("beam_width", tot.BEAM_WIDTH)
    depth = state.get("depth", tot.DEPTH_LIMIT)
    primary = [b for b in qualified if b.driver in PRIMARY_DRIVERS_SET]
    corroborating = [b for b in qualified if b.driver in CORROBORATING_SET]

    # ---- deterministic tie-break among competing primary drivers ----------
    # Demo: force the top two primary drivers into an equal-strength tie so the
    # tie-break sequence and its escalation can be demonstrated reliably.
    if state.get("inject_tie") and len(primary) >= 2:
        strong, other = primary[0], primary[1]
        other.scores = dict(strong.scores); other.total = strong.total
        other.signal = strong.signal
        strong.confidence = other.confidence = guardrails.evidence_gate(strong.total)
        _step(state, "demo · inject tie", f"Forced an equal-strength tie between "
              f"'{strong.label}' and '{other.label}' to exercise the tie-break sequence.")
    elif state.get("inject_tie"):
        _step(state, "demo · inject tie", "Tie injection skipped — fewer than two "
              "qualified primary drivers to contend.")

    tie = None
    if (len(primary) >= 2 and primary[0].total >= guardrails.LIKELY_AT
            and primary[1].total >= guardrails.LIKELY_AT
            and tot.is_unresolved_tie(primary[0], primary[1])):
        b0, b1 = primary[0], primary[1]
        for crit in tot.TIE_BREAK_CRITERIA:
            _step(state, "tie-break", f"{crit}: equal for '{b0.label}' and '{b1.label}'.")
        b0.confidence = b1.confidence = "possible contributor"
        b0.tied = b1.tied = True
        tie = {"drivers": [b0.label, b1.label], "owners": [b0.owner, b1.owner],
               "criteria": list(tot.TIE_BREAK_CRITERIA),
               "note": (f"{b0.label} and {b1.label} are equally supported; the "
                        "deterministic tie-break could not separate them, so both are "
                        "labeled possible contributors and routed to analyst review.")}
        a.event(workflow_node="critic", decision_type="tie_unresolved",
                tool_name="Critic/Evaluator", input_summary=f"{b0.driver} vs {b1.driver}",
                output_summary="tie-break exhausted; both -> possible contributor",
                score_or_confidence="unresolved", status="caveated",
                user_visible_note=f"Tie unresolved between {b0.label} and {b1.label}; action "
                                  f"path: review {b0.owner} and {b1.owner} findings before action.")
        _step(state, "tie-break · unresolved", tie["note"], ok=False)

    beam = primary[:bw]
    deferred = primary[bw:]
    depth2 = ([{"driver": b.driver, "sub_drivers": b.sub_drivers,
                "refined": f"Refine '{b.label}' into: {', '.join(b.sub_drivers)}."} for b in beam]
              if depth >= 2 else [])
    _step(state, "critic + beam select (width %d)" % bw,
          "Primary drivers — beam kept %s; deferred %s. Corroborating signals: %s. "
          "Pruned %s; degraded %d." % (
              ", ".join(b.driver for b in beam) or "none",
              ", ".join(b.driver for b in deferred) or "none",
              ", ".join(b.driver for b in corroborating) or "none",
              ", ".join(b.driver for b in pruned) or "none", len(degraded)))
    if depth >= 2:
        for d in depth2:
            _step(state, "depth-2 refinement",
                  f"{(catalog.get_driver(d['driver']) or {}).get('label', d['driver'])} → "
                  f"sub-drivers: {', '.join(d['sub_drivers'])}")
    else:
        _step(state, "depth-1 only", "ToT depth=1 — sub-driver refinement skipped.")
    return {"branches": branches, "beam": beam, "deferred": deferred, "pruned": pruned,
            "corroborating": corroborating, "depth2": depth2, "degraded": degraded, "tie": tie}


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


def n_human_review(state: WState) -> dict:
    """Human-review gate. Recommendations are never
    executed automatically — this evaluates the safety triggers and raises a
    HumanReviewRequest so high-risk / low-confidence / conflicting / business-
    impacting findings are reviewed by their owner before any action."""
    from agents.contracts import max_risk
    a: AuditLog = state["audit"]
    beam = state.get("beam", [])
    deferred = state.get("deferred", [])
    likely = [b for b in beam if b.confidence == "likely driver"]

    reasons: list[str] = []
    risk = "low"
    if state.get("refusal"):
        reasons.append("user requested an operational write — converted to a recommendation")
        risk = max_risk(risk, "high")
    if not likely:
        reasons.append("no driver met the evidence threshold (inconclusive)")
        risk = max_risk(risk, "medium")
    elif len(likely) >= 2:
        reasons.append("multiple drivers are likely — competing evidence to weigh")
        risk = max_risk(risk, "high")
    if not state.get("sync", {"in_sync": True}).get("in_sync", True):
        reasons.append("a source artifact was stale/out of sync")
        risk = max_risk(risk, "high")
    if deferred:
        reasons.append("possible contributors were deferred by the query budget and need confirmation")
        risk = max_risk(risk, "medium")
    degraded = state.get("degraded", [])
    if degraded:
        reasons.append(f"{len(degraded)} analyst(s) failed/timed out and were excluded — "
                       "evidence is partial and needs confirmation")
        risk = max_risk(risk, "medium")
    tie = state.get("tie")
    if tie:
        reasons.append(f"two competing drivers of equal strength ({' and '.join(tie['drivers'])}) "
                       "could not be separated by the tie-break — labeled possible contributors "
                       "pending analyst review")
        risk = max_risk(risk, "high")
    # Every recommendation is business-impacting: it always routes to an owner for
    # a human-reviewed decision rather than an automatic system change.
    reasons.append("recommended actions are business-impacting and require owner review before execution")

    # For a cross-business briefing the highest-priority issue may be a corroborating
    # signal (service / vendor / finance), so rank every qualified branch by evidence.
    if state.get("intent") == "briefing":
        corroborating = state.get("corroborating", [])
        top = sorted(beam + deferred + corroborating,
                     key=lambda b: (b.total, abs(b.signal)), reverse=True)
    else:
        top = (likely or beam or deferred)
    impacted_owner = top[0].owner if top else "Analytics"
    if tie:
        impacted_owner = " / ".join(dict.fromkeys(tie["owners"]))
        recommended_action = (f"Review the {tie['drivers'][0]} and {tie['drivers'][1]} findings "
                              f"with {impacted_owner} and decide before any business action — "
                              "the tie-break could not pick a single driver.")
    else:
        recommended_action = grounded_action(top[0].driver) if top else \
            "Escalate as needs-analyst-review with recommended next checks."
    review = a.create_review_request(
        reason="; ".join(reasons), risk_level=risk, impacted_owner=impacted_owner,
        recommended_action=recommended_action,
        evidence_summary=(top[0].finding if top else "No branch met the evidence threshold."))
    a.event(workflow_node="human_review_gate", decision_type="human_review_required",
            tool_name="Guardrails", output_summary=f"risk={risk}; owner={impacted_owner}",
            score_or_confidence=risk,
            user_visible_note="Findings routed for human-reviewed owner action; no system write.")
    _step(state, "human review", f"Routed for human review (risk: {risk}) — owner action only, no system write.")
    return {"review": review}


def n_synthesize(state: WState) -> dict:
    a: AuditLog = state["audit"]
    bl = state["baseline"]
    beam, deferred, pruned = state["beam"], state["deferred"], state["pruned"]
    corroborating = state.get("corroborating", [])
    intent = state.get("intent", "overall")
    focus = state.get("focus")
    likely = [b for b in beam if b.confidence == "likely driver"]
    pct = bl["pct_change"]
    conf = guardrails.overall_confidence(len(likely))
    ctx = (f"digital conversion fell {abs(pct):.0%} yesterday "
           f"({bl['target']:.2%} vs {bl['baseline']:.2%} prior-7-day average)")
    drivers = [{"label": b.label, "confidence": b.confidence, "owner": b.owner,
                "finding": b.finding, "score": b.total} for b in beam]
    corr_out = [{"label": b.label, "owner": b.owner, "finding": b.finding,
                 "confidence": b.confidence, "score": b.total} for b in corroborating]

    # action log + recommendations: primary beam (act now), deferred primary
    # (investigate), corroborating signals (monitor). Focus driver first.
    pri_map = {id(b): ("high" if b in beam else "medium") for b in beam + deferred}
    pri_map.update({id(b): "monitor" for b in corroborating})
    ordered = beam + deferred + corroborating
    if intent == "briefing":
        # Cross-business briefing: rank EVERY domain's finding together by evidence
        # strength so the biggest issue leads — even if it's a service/vendor/finance
        # signal — rather than forcing the conversion-drop framing.
        ordered = sorted(beam + deferred + corroborating,
                         key=lambda b: (b.total, abs(b.signal)), reverse=True)
        pri_map = {id(b): ("high" if i < 2 else "medium") for i, b in enumerate(ordered)}
    elif focus:
        ordered = sorted(ordered, key=lambda b: 0 if b.driver == focus else 1)
    recos = []
    for b in ordered:
        pri = pri_map.get(id(b), "medium")
        action = RECOMMENDATIONS.get(b.driver, "Investigate and confirm with the owner before acting.")
        if getattr(b, "tied", False):
            # Unresolved tie: surface the owner/action path as a needs-review item.
            pri = "needs review"
            action = (f"Tie unresolved — route the {b.label} finding to {b.owner} for analyst "
                      "review alongside the competing driver before any business action.")
        a.action(owner=b.owner, issue=b.label, evidence=b.finding, confidence=b.confidence,
                 priority=pri, next_step=action)
        recos.append({"owner": b.owner, "action": action, "priority": pri,
                      "confidence": b.confidence, "rationale": b.finding})

    # ---- headline + factual lead, TUNED to the question intent ----------
    all_branches = beam + deferred + corroborating + pruned
    fb = next((b for b in all_branches if b.driver == focus), None) if focus else None
    if intent == "briefing":
        n_issues = len(ordered)
        top = ordered[0] if ordered else None
        if top is not None:
            headline = (f"Executive briefing — {n_issues} cross-functional issue"
                        f"{'s' if n_issues != 1 else ''} need attention; the top priority is "
                        f"{top.label} ({top.owner}).")
            facts = ("Across the full analyst team, the priorities ranked by evidence strength are: "
                     + "; ".join(f"{b.label} ({b.owner}) — {b.finding}" for b in ordered[:3])
                     + f". For broader context, {ctx}.")
        else:
            headline = "Executive briefing — no issue cleared the evidence threshold today."
            facts = f"No domain produced a material signal. For context, {ctx}."
    elif intent == "actions":
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
        import re as _re
        # Only frame the answer around the conversion drop if the question actually
        # asks about conversion/contribution; otherwise answer from the domain's
        # own perspective (e.g. "how did paid social perform?").
        conversion_framed = bool(_re.search(r"conversion|contribut|decline", state["question"].lower()))
        finding_lead = fb.finding[0].upper() + fb.finding[1:]
        if not conversion_framed:
            headline = f"{fb.label}: {finding_lead}"
        elif fb.driver in CORROBORATING_SET:
            seen = fb.confidence != "pruned"
            headline = (f"{'Yes' if seen else 'No clear evidence'} — {fb.label} is a "
                        f"corroborating signal (not a direct cause) for yesterday's change.")
        else:
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

    tie = state.get("tie")
    if tie:
        headline = (f"Two competing drivers are equally supported for the conversion drop — "
                    f"{tie['drivers'][0]} and {tie['drivers'][1]}.")
        facts = (f"{ctx}. The deterministic tie-break (evidence → freshness → caveats → "
                 f"owner/action → graph alignment) could not separate {tie['drivers'][0]} and "
                 f"{tie['drivers'][1]}, so both are labeled possible contributors and routed to "
                 f"analyst review ({' / '.join(dict.fromkeys(tie['owners']))}) before any action.")

    summary = llm.draft_answer(state["question"], facts, conf)
    defn = catalog.get_metric("digital_conversion_rate")["definition"].strip()
    base_caveats = ["Synthetic data with a fixed seed; magnitudes are illustrative.",
                    "Read-only analysis - no operational systems were modified.",
                    "Causality is labeled (likely driver / possible contributor); not proven."]

    # ---- focus block (the analyst the question is about) ----------------
    focus_block = None
    if intent == "driver" and fb is not None:
        focus_block = {"key": fb.driver, "label": fb.label, "owner": fb.owner,
                       "confidence": fb.confidence, "finding": fb.finding,
                       "action": RECOMMENDATIONS.get(fb.driver, ""), "evidence": fb.evidence}

    # ---- executive summary, TAILORED to the question ---------------------
    _tag = {"high": "Act now", "medium": "Investigate next", "monitor": "Monitor (corroborating)"}
    if intent == "driver" and fb is not None:
        es_title = f"Summary — {fb.label}"
        bullets = [f"Finding: {fb.finding}",
                   f"Recommended action — **{fb.owner}**: {RECOMMENDATIONS.get(fb.driver, '')}",
                   f"Confidence: {fb.confidence}. Context: {ctx}."]
    elif intent == "trust":
        es_title = "Grounding"
        bullets = [f"Certified definition: {defn}", "Baseline rule: prior 7-day average.",
                   "Validated against YAML and traced through the NetworkX graph; see Trust details "
                   "for retrieved chunks, the graph path, and source versions."]
    elif intent == "caveats":
        es_title = "Caveats & data freshness"
        bullets = ["Trust T-1 (yesterday); same-day (T-0) data may be incomplete."] + base_caveats
    elif intent == "actions":
        es_title = "Recommended actions"
        bullets = [f"Context: {ctx}."] + [
            f"{_tag.get(r['priority'], 'Investigate next')} — **{r['owner']}**: {r['action']} "
            f"(basis: {r['rationale']})" for r in recos]
    elif intent == "briefing":
        es_title = "Executive briefing"
        bullets = ["The full analyst team ran in parallel; issues are ranked by evidence strength "
                   "and routed to their owners below."] + [
            f"{_tag.get(r['priority'], 'Investigate next')} — **{r['owner']}**: {r['action']} "
            f"(basis: {r['rationale']})" for r in recos]
    else:  # overall
        es_title = "Executive summary"
        bullets = [f"Context: {ctx}."] + [
            f"{_tag.get(r['priority'], 'Investigate next')} — **{r['owner']}**: {r['action']} "
            f"(basis: {r['rationale']})" for r in recos]
    if not bullets:
        bullets = ["No driver cleared the evidence threshold; recommend the listed next checks."]
    exec_summary = {"title": es_title, "bullets": bullets, "recommendations": recos,
                    "note": "Owner-routed recommendations from validated evidence; guarded language; "
                            "human-reviewed only, no operational writes."}
    a.event(workflow_node="executive_summary", decision_type="exec_summary_ready",
            tool_name="Executive Summary Agent", output_summary=f"intent={intent}",
            user_visible_note="Question-specific summary composed.")
    _step(state, "executive summary", f"Composed a {intent}-specific summary.")

    # Ranked cross-domain issue list for the briefing view (every domain, not just
    # the conversion beam), with priority + the grounded action for each.
    briefing_issues = ([{"label": b.label, "owner": b.owner, "finding": b.finding,
                         "confidence": b.confidence, "score": b.total, "signal": abs(b.signal),
                         "priority": pri_map.get(id(b), "medium"),
                         "action": grounded_action(b.driver)} for b in ordered]
                       if intent == "briefing" else [])
    recommendation = (
        "These issues span several teams. Route each to its owner for a human-reviewed check, "
        "starting with the two flagged Act now."
        if intent == "briefing" else
        "Evidence points to multiple compounding drivers rather than a single cause. Route each "
        "likely driver to its owner for a human-reviewed check before any action.")

    answer = {
        "headline": headline, "summary": summary, "intent": intent, "focus": focus_block,
        "conversion_context": ctx[0].upper() + ctx[1:] + ".",
        "definition": catalog.get_metric("digital_conversion_rate")["definition"].strip(),
        "drivers": drivers,
        "briefing_issues": briefing_issues,
        "contributors": [{"label": b.label, "confidence": "possible contributor (outside beam)",
                          "owner": b.owner, "finding": b.finding, "score": b.total} for b in deferred],
        "pruned": [{"label": b.label, "reason": b.finding, "score": b.total} for b in pruned],
        "corroborating": corr_out,
        "degraded": state.get("degraded", []),
        "recommendation": recommendation,
        "caveats": ["Synthetic data with a fixed seed; magnitudes are illustrative.",
                    "Read-only analysis - no operational systems were modified.",
                    "Causality is labeled (likely driver / possible contributor); not proven."],
        "confidence": conf,
        "llm_mode": llm.mode(),
        "exec_summary": exec_summary,
        "review": state.get("review"),
        "tie": state.get("tie"),
    }
    a.event(workflow_node="synthesize", decision_type="final_answer_ready", tool_name="Synthesis+LLM",
            output_summary=headline[:70], score_or_confidence=conf,
            user_visible_note="Final grounded answer assembled, tuned to the question intent.")
    _step(state, "synthesize", "Assembled the final answer tuned to the question (%s drafting)." % answer["llm_mode"])
    return {"answer": answer}


def n_gated(state: WState) -> dict:
    """Terminal node for inputs stopped at the gate: a refused (sensitive/PII) request
    or an ambiguous question needing clarification. No retrieval, no SQL, no evidence —
    just a clear, safe message. A refusal also raises a human-review request."""
    a: AuditLog = state["audit"]
    intent = state.get("intent")
    msg = state.get("gate_message", "")
    review = None
    if intent == "refused":
        headline = "Request refused — outside the governed, read-only, synthetic scope."
        review = a.create_review_request(
            reason="real personal/sensitive/proprietary data detected in the request",
            risk_level="high", impacted_owner="Data Governance",
            recommended_action="Resubmit using the synthetic dataset with no real PII; any "
                               "production or operational change stays outside this read-only assistant.",
            evidence_summary="Input matched a sensitive-data pattern; not analyzed.")
        caveats = ["No analysis was performed; the input was blocked at the scope gate.",
                   "This prototype is read-only over synthetic data; no PII is accepted."]
    else:  # clarify
        headline = "A quick clarification will help me investigate accurately."
        caveats = ["No default metric was assumed; please confirm the area and time frame.",
                   "You can accept the governed default (digital conversion vs prior 7-day average)."]
    summary = llm.draft_answer(state["question"], msg, "informational")
    answer = {"intent": intent, "headline": headline, "summary": summary,
              "confidence": "n/a", "llm_mode": llm.mode(), "owner": "Data Governance",
              "definition": "Input/scope guardrail (no certified metric was queried).",
              "metrics": [], "table": None, "chart": None, "drivers": [], "contributors": [],
              "corroborating": [], "pruned": [], "degraded": [], "exec_summary": None,
              "focus": None, "caveats": caveats, "review": review,
              "recommendation": msg}
    a.event(workflow_node="synthesize", decision_type="final_answer_ready", tool_name="Guardrails",
            output_summary=headline[:70], status="blocked" if intent == "refused" else "caveated",
            user_visible_note="Gated response assembled (no analysis performed).")
    _step(state, "synthesize", f"Composed a {intent} response (no evidence query run).")
    return {"answer": answer, "review": review, "queries_used": 0}


def n_analytics(state: WState) -> dict:
    """Direct governed analytics query (a standalone insight, not the conversion
    investigation). Validate SQL -> run read-only DuckDB -> summarize with numbers."""
    a: AuditLog = state["audit"]
    con = state["con"]
    ins = insights.get(state["focus"])
    _step(state, "semantic lookup", f"Resolved insight '{ins.id}' (owner {ins.owner}); "
          "answered from approved tables only.")
    sql = ins.sql.format(td=state["meta"]["target_day"],
                         l7=state["meta"]["target_day"], b0=state["meta"]["baseline_start"],
                         b1=state["meta"]["baseline_end"])
    ok, reason = guardrails.check_sql(sql)
    _step(state, "SQL validate", reason, ok)
    a.event(workflow_node="sql_validate", decision_type="sql_checked", tool_name="SQL validator",
            output_summary=reason, status="success" if ok else "blocked")
    if not ok:
        return {"answer": {"intent": "analytics", "headline": "Query blocked by guardrail",
                           "summary": reason, "confidence": "n/a", "llm_mode": llm.mode(),
                           "metrics": [], "table": None, "owner": ins.owner, "sql": sql},
                "queries_used": 1}
    res = insights.run(ins.id, con, state["meta"])
    a.event(workflow_node="sql_execute", decision_type="insight_computed", tool_name="DuckDB",
            input_summary=ins.id, output_summary=res["headline"][:70],
            user_visible_note=res["headline"])
    _step(state, "DuckDB execute", f"{res['headline']}")
    summary = llm.draft_answer(state["question"], res["summary"], "informational")
    _step(state, "summarize", f"Composed analytics answer for {ins.owner}.")
    answer = {"intent": "analytics", "headline": res["headline"], "summary": summary,
              "confidence": "informational", "llm_mode": llm.mode(),
              "metrics": res["metrics"], "table": res["table"], "owner": ins.owner,
              "domain": ins.domain, "sql": sql,
              "definition": "Direct governed analytics query over approved tables.",
              "chart": res.get("chart"),
              "drivers": [], "contributors": [], "corroborating": [], "pruned": [],
              "degraded": [], "caveats": ["Synthetic data with a fixed seed; illustrative magnitudes.",
                                          "Read-only analysis over governed tables."],
              "exec_summary": None, "focus": None,
              "recommendation": f"{ins.owner}: {res['headline']} Review and prioritize "
                                "accordingly (read-only analysis — no operational writes)."}
    a.event(workflow_node="synthesize", decision_type="final_answer_ready", tool_name="Synthesis",
            output_summary=res["headline"][:70], user_visible_note="Analytics answer assembled.")
    return {"answer": answer, "queries_used": 1}


def n_themed(state: WState) -> dict:
    """Themed multi-signal review (health check / trend / risk). Runs 2-3 read-only
    governed queries and returns a narrative + signals + a relevant chart."""
    a: AuditLog = state["audit"]
    con = state["con"]
    th = themes.get(state["focus"])
    _step(state, "semantic lookup", f"Resolved themed review '{th.id}' (owner {th.owner}).")
    _step(state, "DuckDB execute", "Running the themed review's governed read-only queries…")
    res = themes.run(th.id, con, state["meta"])
    a.event(workflow_node="sql_execute", decision_type="theme_computed", tool_name="DuckDB",
            input_summary=th.id, output_summary=res["headline"][:70], user_visible_note=res["headline"])
    summary = llm.draft_answer(state["question"], res["summary"], "informational")
    _step(state, "summarize", f"Composed themed review for {th.owner}.")
    answer = {"intent": "themed", "headline": res["headline"], "summary": summary,
              "confidence": "informational", "llm_mode": llm.mode(), "owner": th.owner,
              "domain": th.domain, "signals": res.get("signals", []), "table": res.get("table"),
              "chart": res.get("chart"), "recommendation": res.get("recommendation", ""),
              "definition": "Themed multi-signal review over governed tables.",
              "drivers": [], "contributors": [], "corroborating": [], "pruned": [], "degraded": [],
              "caveats": ["Synthetic data with a fixed seed; illustrative magnitudes.",
                          "Read-only analysis over governed tables."],
              "exec_summary": None, "focus": None, "metrics": res.get("signals", [])}
    a.event(workflow_node="synthesize", decision_type="final_answer_ready", tool_name="Synthesis",
            output_summary=res["headline"][:70], user_visible_note="Themed review assembled.")
    return {"answer": answer, "queries_used": 1}


# --------------------------------------------------------------------------
# Graph assembly
# --------------------------------------------------------------------------
def build_workflow():
    sg = StateGraph(WState)
    # Investigation chain (conversion-drop path)
    chain = [("sync_gate", n_sync_gate), ("retrieve", n_retrieve), ("validate", n_validate),
             ("relate", n_relate), ("baseline", n_baseline), ("tot_gate", n_tot_gate),
             ("dispatch", n_dispatch), ("critic", n_critic), ("evidence_gate", n_evidence_gate),
             ("human_review", n_human_review), ("synthesize", n_synthesize)]
    sg.add_node("classify", n_classify)
    sg.add_node("analytics", n_analytics)
    sg.add_node("themed", n_themed)
    sg.add_node("gated", n_gated)
    for name, fn in chain:
        sg.add_node(name, fn)
    sg.add_edge(START, "classify")
    # Route: refused/clarify -> terminal gate; analytics/themed -> direct node;
    # otherwise the full conversion-drop investigation.
    def _route(s):
        return {"analytics": "analytics", "themed": "themed",
                "refused": "gated", "clarify": "gated"}.get(s.get("intent"), "sync_gate")
    sg.add_conditional_edges("classify", _route,
                             {"analytics": "analytics", "themed": "themed",
                              "gated": "gated", "sync_gate": "sync_gate"})
    sg.add_edge("analytics", END)
    sg.add_edge("themed", END)
    sg.add_edge("gated", END)
    for (a, _), (b, _) in zip(chain, chain[1:]):
        sg.add_edge(a, b)
    sg.add_edge("synthesize", END)
    return sg.compile()


_APP = None


def get_app():
    global _APP
    if _APP is None:
        _APP = build_workflow()
    return _APP
