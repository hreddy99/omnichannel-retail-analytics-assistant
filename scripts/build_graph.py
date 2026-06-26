#!/usr/bin/env python3
"""Build the NetworkX knowledge graph from the YAML catalog and report its shape
(node counts by type, edge count, freshness gate). Useful as a quick health check
that the catalog -> graph projection is intact.
"""
import _bootstrap  # noqa: F401  (puts repo root on sys.path)

from collections import Counter

from skills import graph_skill as graph


def main() -> int:
    g = graph.build_graph()
    kinds = Counter(data.get("kind", "?") for _, data in g.nodes(data=True))
    print(f"nodes : {g.number_of_nodes()}")
    for kind, n in sorted(kinds.items()):
        print(f"  {kind:10s} {n}")
    print(f"edges : {g.number_of_edges()}")
    print(f"fresh : {graph.is_fresh(g)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
