#!/usr/bin/env python3
"""Validate the governed YAML catalog: it loads, every file has a content hash,
and the approved-table allow-list is non-empty. The catalog is the source of
truth, so this is a cheap gate to run before launching the app.
"""
import _bootstrap  # noqa: F401  (puts repo root on sys.path)

from skills import catalog_skill as catalog


def main() -> int:
    cat = catalog.load_catalog()
    hashes = catalog.file_hashes()
    tables = catalog.approved_tables()
    print(f"catalog_version : {catalog.version()}")
    print(f"content_hash    : {catalog.content_hash()}")
    print(f"files hashed    : {len(hashes)}")
    for name, h in sorted(hashes.items()):
        print(f"  {name:18s} {h}")
    print(f"approved tables : {len(tables)}")
    ok = bool(hashes) and bool(tables) and "metrics" in cat
    print("\n", "CATALOG OK" if ok else "CATALOG INVALID")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
