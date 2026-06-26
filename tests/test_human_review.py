"""Typed contracts and the human-review gate."""
from agents.contracts import (AgentTask, AgentFinding, BranchState, AuditEvent,
                              HumanReviewRequest, max_risk)
from app import content as P
from workflows.investigation import run_investigation


def test_contracts_instantiate_and_serialize():
    for obj in [
        AgentTask(run_id="r", task_id="t", agent_name="a", metric_id="m", date_range="d"),
        AgentFinding(task_id="t", agent_name="a", status="ok", evidence_summary="e"),
        BranchState(branch_id="b", driver="d", depth=1, evidence_plan="p",
                    source_version="v", score=9.0, keep_or_prune="keep"),
        AuditEvent(run_id="r", event_id="e", timestamp="ts", workflow_node="n",
                   tool_name="tool", decision_type="dec"),
        HumanReviewRequest(run_id="r", reason="why", risk_level="high",
                           impacted_owner="o", recommended_action="act"),
    ]:
        assert isinstance(obj.to_dict(), dict)


def test_max_risk():
    assert max_risk("low", "high") == "high"
    assert max_risk("medium", "low") == "medium"


def test_clean_investigation_runs_team_without_forcing_review():
    # A routine, well-supported investigation goes through the multi-agent team but does
    # NOT auto-trigger human review (review fires only on Checkpoint-6 conditions).
    t = run_investigation(P.DEMO_QUESTIONS[0], use_index=False)
    assert t["answer"]["intent"] == "overall"
    assert t["answer"]["drivers"]          # the analyst team still ran
    assert t["coordination"]["n_ok"] >= 1  # parallel dispatch happened
    assert t["answer"]["review"] is None   # no review banner forced


def test_degraded_investigation_raises_human_review():
    # A genuine condition (an analyst failing) DOES route to human review.
    t = run_investigation(P.DEMO_QUESTIONS[0], use_index=False, inject_failure="campaign_mix")
    rv = t["answer"]["review"]
    assert rv is not None
    assert rv["risk_level"] in {"low", "medium", "high"}
    assert rv["impacted_owner"]
    assert rv["status"] == "pending review"
    assert t["audit"].reviews  # recorded on the audit log


def test_write_request_is_refused_and_flagged_high_risk():
    t = run_investigation("Pause the paid social campaign and update inventory", use_index=False)
    rv = t["answer"]["review"]
    assert rv["risk_level"] == "high"
    assert "write" in rv["reason"]
