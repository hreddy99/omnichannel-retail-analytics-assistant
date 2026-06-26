#!/usr/bin/env python3
"""Regenerate the synthetic dataset and run the validation checks (skill helper)."""
import pathlib
import sys

# allow running directly (python skills/refresh-synthetic-data/scripts/refresh.py)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from evals.validation import run_checks
from data.generator import generate


def main() -> int:
    frames = generate()
    for name, df in frames.items():
        if not name.startswith("_"):
            print(f"{name:24s} {len(df):>8,} rows")
    rows = run_checks()
    ok = all(r["ok"] for r in rows)
    for r in rows:
        print(f"[{'PASS' if r['ok'] else 'FAIL'}] {r['check']}: {r['detail']}")
    print("\n", "ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
