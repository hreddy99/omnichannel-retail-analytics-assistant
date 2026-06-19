"""Knowledge-graph coverage: every governed driver resolves a
driver -> tables -> owner path (Checkpoint 6 graph accuracy)."""
from skills import catalog_skill as catalog, graph_skill as graph


def test_every_driver_routes_to_tables_and_owner():
    g = graph.build_graph()
    drivers = list((catalog.load_catalog().get("drivers") or {}).keys())
    assert drivers
    for d in drivers:
        path = graph.driver_path(g, d)
        assert path is not None, f"no graph path for driver {d}"
        assert path["tables"], f"driver {d} has no tables"
        assert path["owner"], f"driver {d} has no owner"


def test_stale_graph_blocks_traversal():
    """A graph stamped with a wrong version is treated as stale (returns None)."""
    g = graph.build_graph()
    g.graph["catalog_version"] = "0.0.0-stale"
    assert graph.driver_path(g, "inventory_availability") is None
