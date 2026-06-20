"""
Investigation orchestrator (public entry point used by the Streamlit app).

Wires the governed layers together and invokes the multi-agent LangGraph
workflow (workflows/graph.py), returning a single trace dict consumed by the UI.

Two entry points:
  * run_investigation()        - run to completion, return the trace.
  * run_investigation_stream() - generator that yields each decision-log step as
                                 the workflow executes it (for live UI progress),
                                 then yields ("done", trace).
"""
from __future__ import annotations

from skills import catalog_skill as catalog, graph_skill as graph, retrieval_skill as retrieval
from skills.audit_skill import AuditLog
from skills.tot_skill import BEAM_WIDTH, QUERY_BUDGET  # re-export for the UI
from data.generator import build_duckdb, get_meta
from workflows.graph import get_app

__all__ = ["run_investigation", "run_investigation_stream", "BEAM_WIDTH", "QUERY_BUDGET"]


def _setup(question, seed, use_index, inject_failure, top_k, beam_width, depth, inject_tie):
    con = build_duckdb(seed)
    audit = AuditLog()
    state = {"question": question, "con": con, "g": graph.build_graph(),
             "meta": get_meta(seed), "audit": audit,
             "index": retrieval.get_index() if use_index else None,
             "inject_failure": inject_failure, "inject_tie": inject_tie,
             "top_k": top_k, "beam_width": beam_width, "depth": depth}
    return con, audit, state


def _trace(result: dict, audit: AuditLog, question: str) -> dict:
    return {
        "question": question,
        "steps": audit.steps,
        "retrieval": result.get("retrieval", []),
        "baseline": result.get("baseline", {}),
        "tot_activated": result.get("tot_activated", False),
        "agent_results": result.get("agent_results", []),
        "coordination": result.get("coordination", {}),
        "degraded": result.get("degraded", []),
        "depth1": result.get("branches", []),
        "beam": result.get("beam", []),
        "deferred": result.get("deferred", []),
        "pruned": result.get("pruned", []),
        "corroborating": result.get("corroborating", []),
        "depth2": result.get("depth2", []),
        "queries_used": result.get("queries_used", 0),
        "answer": result.get("answer", {}),
        "refusal": result.get("refusal"),
        "tie": result.get("tie"),
        "audit": audit,
        "catalog_version": catalog.version(),
        "catalog_hash": catalog.content_hash(),
    }


def run_investigation(question: str, seed: int = 42, use_index: bool = True,
                      inject_failure: str | None = None, top_k: int = 5,
                      beam_width: int = 2, depth: int = 2, inject_tie: bool = False) -> dict:
    """Execute the full governed multi-agent workflow and return a structured trace.

    The app runs unified: the full specialized analyst team is dispatched every time.
    top_k / beam_width / depth are tunable to explore their impact on the answer.
    inject_tie forces an equal-strength tie between the top two drivers (demo only).
    """
    con, audit, state = _setup(question, seed, use_index, inject_failure, top_k,
                               beam_width, depth, inject_tie)
    result = get_app().invoke(state)
    con.close()
    return _trace(result, audit, question)


def run_investigation_stream(question: str, seed: int = 42, use_index: bool = True,
                             inject_failure: str | None = None, top_k: int = 5,
                             beam_width: int = 2, depth: int = 2, inject_tie: bool = False):
    """Generator yielding ('step', step_dict) as the workflow executes each node,
    then ('done', trace). Lets the UI show actual executing steps live, including
    the (potentially slow, one-time) setup so progress is visible immediately."""
    def prep(detail):
        return ("step", {"node": "prepare", "detail": detail, "ok": True})

    # Setup can be slow on the FIRST run (synthetic-data build + one-time embedding
    # model download). Emit progress so the user sees activity, not a blank spinner.
    yield prep("Generating synthetic retail data (DuckDB)…")
    con = build_duckdb(seed)
    audit = AuditLog()
    g = graph.build_graph()
    yield prep("Loading the governed vector index (first run downloads the embedding model — one time)…")
    index = retrieval.get_index() if use_index else None
    yield prep("Knowledge layers ready — starting the governed workflow.")

    state = {"question": question, "con": con, "g": g, "meta": get_meta(seed),
             "audit": audit, "index": index, "inject_failure": inject_failure,
             "inject_tie": inject_tie,
             "top_k": top_k, "beam_width": beam_width, "depth": depth}
    result: dict = {}
    seen = 0
    # stream_mode="values" yields the full state after each superstep; audit.steps
    # grows as nodes run, so we emit newly-recorded steps as they appear.
    for snapshot in get_app().stream(state, stream_mode="values"):
        result = snapshot
        while seen < len(audit.steps):
            yield ("step", audit.steps[seen])
            seen += 1
    while seen < len(audit.steps):     # flush any final steps
        yield ("step", audit.steps[seen])
        seen += 1
    con.close()
    yield ("done", _trace(result, audit, question))

