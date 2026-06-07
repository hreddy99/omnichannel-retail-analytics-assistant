"""
Investigation orchestrator (public entry point used by the Streamlit app).

Wires the governed layers together and invokes the LangGraph workflow
(src/workflow.py), returning a single trace dict consumed by the UI. Keeps the
`run_investigation` signature stable across the refactor.
"""
from __future__ import annotations

from . import catalog, graph, retrieval
from .audit import AuditLog
from .synthetic_data import build_duckdb, get_meta
from .tot import BEAM_WIDTH, QUERY_BUDGET  # re-export for the UI
from .workflow import get_app

__all__ = ["run_investigation", "BEAM_WIDTH", "QUERY_BUDGET"]


def run_investigation(question: str, seed: int = 42, use_index: bool = True) -> dict:
    """Execute the full governed workflow and return a structured trace."""
    con = build_duckdb(seed)
    g = graph.build_graph()
    meta = get_meta(seed)
    audit = AuditLog()
    index = retrieval.get_index() if use_index else None

    state = {"question": question, "con": con, "g": g, "meta": meta,
             "audit": audit, "index": index}
    result = get_app().invoke(state)
    con.close()

    return {
        "question": question,
        "steps": audit.steps,
        "retrieval": result.get("retrieval", []),
        "baseline": result.get("baseline", {}),
        "tot_activated": result.get("tot_activated", False),
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
