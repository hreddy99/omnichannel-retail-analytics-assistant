#!/usr/bin/env python3
"""Regenerate the synthetic dataset and print row counts per table.

Read-only, synthetic only (Faker, fixed seed); no PII. The data lives in an
in-memory DuckDB at runtime - this script just exercises the generator and
reports the shape of each fact_/dim_ table.
"""
import _bootstrap  # noqa: F401  (puts repo root on sys.path)

from data.generator import generate


def main() -> int:
    frames = generate()
    for name, df in sorted(frames.items()):
        if not name.startswith("_"):
            print(f"{name:24s} {len(df):>9,} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
