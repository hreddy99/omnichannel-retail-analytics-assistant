#!/usr/bin/env python3
"""Pre-warm the local ChromaDB retrieval index (downloads the embedding model
once). Non-fatal: if the model can't be fetched, retrieval falls back to a
deterministic hashing embedder at runtime, so this only speeds up the first run.
"""
import _bootstrap  # noqa: F401  (puts repo root on sys.path)

from skills.retrieval_skill import get_index


def main() -> int:
    idx = get_index()
    print(f"embedder : {idx.embedder_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
