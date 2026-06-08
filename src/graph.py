"""
Knowledge graph (Plan section 9, milestone 5).

NetworkX graph generated FROM the YAML catalog and stamped with catalog_version
+ source hash. Node kinds: metric, table, system, driver, owner. Edge types
follow Plan section 9 (measured_by, feeds_table, affects, owned_by, uses,
caveated_by). If the stored version does not match the active catalog, traversal
is blocked and the graph is rebuilt - keeping the graph subordinate to YAML.
"""
from __future__ import annotations

import networkx as nx

from . import catalog


def build_graph() -> nx.DiGraph:
    cat = catalog.load_catalog()
    g = nx.DiGraph(catalog_version=cat["catalog_version"], source_hash=catalog.content_hash())

    def node(nid, kind, label, **kw):
        g.add_node(nid, kind=kind, label=label, **kw)

    # owners + systems
    for o in cat.get("owners", []):
        node(f"owner:{o['name']}", "owner", o["name"], domain=o.get("domain"))
    for s in cat.get("systems", []):
        node(f"system:{s['name']}", "system", s["name"], domain=s.get("domain"))

    # metrics -> tables (measured_by / feeds_table) and owners (owned_by)
    for name, m in cat.get("metrics", {}).items():
        node(f"metric:{name}", "metric", m.get("label", name), owner=m.get("owner"),
             domain=m.get("domain"))
        if m.get("owner"):
            node(f"owner:{m['owner']}", "owner", m["owner"])
            g.add_edge(f"metric:{name}", f"owner:{m['owner']}", rel="owned_by")
        for t in m.get("approved_tables", []):
            node(f"table:{t}", "table", t)
            g.add_edge(f"metric:{name}", f"table:{t}", rel="measured_by")

    # drivers -> metric (affects), tables (uses), owner (owned_by), system (caveated_by)
    for name, d in cat.get("drivers", {}).items():
        node(f"driver:{name}", "driver", d.get("label", name), owner=d.get("owner"),
             domain=d.get("domain"))
        g.add_edge("metric:digital_conversion_rate", f"driver:{name}", rel="affects")
        if d.get("owner"):
            node(f"owner:{d['owner']}", "owner", d["owner"])
            g.add_edge(f"driver:{name}", f"owner:{d['owner']}", rel="owned_by")
        if d.get("system"):
            node(f"system:{d['system']}", "system", d["system"])
            g.add_edge(f"driver:{name}", f"system:{d['system']}", rel="caveated_by")
        for t in d.get("tables", []):
            node(f"table:{t}", "table", t)
            g.add_edge(f"driver:{name}", f"table:{t}", rel="uses")
    return g


def is_fresh(g: nx.DiGraph) -> bool:
    return (g.graph.get("catalog_version") == catalog.version()
            and g.graph.get("source_hash") == catalog.content_hash())


def driver_path(g: nx.DiGraph, driver: str) -> dict | None:
    """Approved relationship path for a driver, or None if blocked/stale."""
    if not is_fresh(g):
        return None
    node = f"driver:{driver}"
    if node not in g:
        return None
    tables = [g.nodes[n]["label"] for n in g.successors(node) if g.nodes[n].get("kind") == "table"]
    owner = next((g.nodes[n]["label"] for n in g.successors(node)
                  if g.nodes[n].get("kind") == "owner"), None)
    system = next((g.nodes[n]["label"] for n in g.successors(node)
                   if g.nodes[n].get("kind") == "system"), None)
    return {"driver": driver, "tables": tables, "owner": owner, "system": system,
            "path": f"digital_conversion_rate --affects--> {driver} --uses--> {tables} "
                    f"--owned_by--> {owner}"}
