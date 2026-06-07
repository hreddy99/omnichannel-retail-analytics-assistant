"""
Knowledge graph (Plan section 6, milestone 5).

NetworkX graph generated FROM the YAML catalog and stamped with catalog_version.
If the stored version does not match the active catalog, traversal is blocked
and the graph is rebuilt - keeping the graph subordinate to YAML truth.
"""
from __future__ import annotations

import networkx as nx

from . import catalog


def build_graph() -> nx.DiGraph:
    cat = catalog.load_catalog()
    g = nx.DiGraph(catalog_version=cat["catalog_version"])

    for name, m in cat.get("metrics", {}).items():
        g.add_node(f"metric:{name}", kind="metric", label=name, owner=m.get("owner"))
        g.add_node(f"owner:{m.get('owner')}", kind="owner", label=m.get("owner"))
        g.add_edge(f"metric:{name}", f"owner:{m.get('owner')}", rel="owned_by")
        for t in m.get("source_tables", []):
            g.add_node(f"table:{t}", kind="table", label=t)
            g.add_edge(f"metric:{name}", f"table:{t}", rel="computed_from")

    for name, d in cat.get("drivers", {}).items():
        g.add_node(f"driver:{name}", kind="driver", label=d.get("label", name),
                   owner=d.get("owner"), domain=d.get("domain"))
        g.add_node(f"owner:{d.get('owner')}", kind="owner", label=d.get("owner"))
        g.add_edge("metric:digital_conversion_rate", f"driver:{name}", rel="explained_by")
        g.add_edge(f"driver:{name}", f"owner:{d.get('owner')}", rel="routed_to")
        for t in d.get("tables", []):
            g.add_node(f"table:{t}", kind="table", label=t)
            g.add_edge(f"driver:{name}", f"table:{t}", rel="interrogates")
    return g


def is_fresh(g: nx.DiGraph) -> bool:
    return g.graph.get("catalog_version") == catalog.version()


def driver_path(g: nx.DiGraph, driver: str) -> dict | None:
    """Return the approved relationship path for a driver, or None if blocked."""
    if not is_fresh(g):
        return None
    node = f"driver:{driver}"
    if node not in g:
        return None
    tables = [g.nodes[n]["label"] for n in g.successors(node)
              if g.nodes[n].get("kind") == "table"]
    owner = next((g.nodes[n]["label"] for n in g.successors(node)
                  if g.nodes[n].get("kind") == "owner"), None)
    return {"driver": driver, "tables": tables, "owner": owner,
            "path": f"digital_conversion_rate -> {driver} -> {tables} -> {owner}"}
