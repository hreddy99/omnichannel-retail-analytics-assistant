"""
Investigation orchestrator (public entry point used by the Streamlit app).

Wires the governed layers together and invokes the multi-agent LangGraph
workflow (src/workflow.py), returning a single trace dict consumed by the UI.

Two entry points:
  * run_investigation()        - run to completion, return the trace.
  * run_investigation_stream() - generator that yields each decision-log step as
                                 the workflow executes it (for live UI progress),
                                 then yields ("done", trace).
"""
from __future__ import annotations

from . import catalog, graph, retrieval
from .audit import AuditLog
from .synthetic_data import build_duckdb, get_meta
from .tot import BEAM_WIDTH, QUERY_BUDGET  # re-export for the UI
from .workflow import get_app

__all__ = ["run_investigation", "run_investigation_stream", "BEAM_WIDTH", "QUERY_BUDGET"]


def _setup(question, seed, use_index, inject_failure):
    con = build_duckdb(seed)
    audit = AuditLog()
    state = {"question": question, "con": con, "g": graph.build_graph(),
             "meta": get_meta(seed), "audit": audit,
             "index": retrieval.get_index() if use_index else None,
             "inject_failure": inject_failure}
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
        "depth2": result.get("depth2", []),
        "queries_used": result.get("queries_used", 0),
        "answer": result.get("answer", {}),
        "refusal": result.get("refusal"),
        "audit": audit,
        "catalog_version": catalog.version(),
        "catalog_hash": catalog.content_hash(),
    }


def run_investigation(question: str, seed: int = 42, use_index: bool = True,
                      inject_failure: str | None = None) -> dict:
    """Execute the full governed multi-agent workflow and return a structured trace.

    The app runs unified: the full specialized analyst team is dispatched every time.
    """
    con, audit, state = _setup(question, seed, use_index, inject_failure)
    result = get_app().invoke(state)
    con.close()
    return _trace(result, audit, question)


def run_investigation_stream(question: str, seed: int = 42, use_index: bool = True,
                             inject_failure: str | None = None):
    """Generator yielding ('step', step_dict) as the workflow executes each node,
    then ('done', trace). Lets the UI show actual executing steps live."""
    con, audit, state = _setup(question, seed, use_index, inject_failure)
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
