"""The Plan section 14.4 data-validation checks must all pass."""
from evals.validation import run_checks


def test_all_validation_checks_pass():
    rows = run_checks()
    failed = [r["check"] for r in rows if not r["ok"]]
    assert not failed, f"failing checks: {failed}"
