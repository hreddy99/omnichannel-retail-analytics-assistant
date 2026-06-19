"""Reasoning is bounded: the anchor investigation respects beam width, depth, and
the query budget — no uncontrolled loops."""
from skills import tot_skill as tot
from workflows.investigation import run_investigation

ANCHOR = "Why did digital conversion drop yesterday compared with the prior 7-day average?"


def test_anchor_respects_budget_and_bounds():
    t = run_investigation(ANCHOR, use_index=False)
    assert len(t["beam"]) <= tot.BEAM_WIDTH
    assert t["queries_used"] <= tot.QUERY_BUDGET
    assert len(t["depth2"]) <= tot.BEAM_WIDTH  # only beam drivers are refined


def test_query_budget_is_consistent_with_team_size():
    # 1 baseline + one read-only query per domain analyst.
    assert tot.QUERY_BUDGET == 1 + tot.N_DOMAIN_ANALYSTS
