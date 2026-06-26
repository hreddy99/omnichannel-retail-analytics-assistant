"""Resilience: a stale source is flagged and escalated, and a failing analyst is
retried once before being escalated as degraded."""
from workflows.investigation import run_investigation

ANCHOR = "Why did digital conversion drop yesterday compared with the prior 7-day average?"


def test_stale_source_is_flagged_and_routed_to_review():
    t = run_investigation(ANCHOR, use_index=False, inject_stale=True)
    assert t["answer"]["review"] is not None
    assert "stale" in t["answer"]["review"]["reason"].lower()
    # the sync-gate decision should be recorded as blocked
    assert any(e["decision_type"] == "catalog_sync_checked" and e["status"] == "blocked"
               for e in t["audit"].events)


def test_failing_analyst_is_retried_once_then_degraded():
    t = run_investigation(ANCHOR, use_index=False, inject_failure="campaign_mix")
    assert t["coordination"]["retries"] >= 1            # one targeted retry attempted
    assert t["degraded"]                                # still failed -> excluded
    assert t["answer"]["review"] is not None            # degraded -> human review
