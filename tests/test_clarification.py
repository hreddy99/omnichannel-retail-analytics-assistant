"""Input guardrails route correctly: PII -> refused, ambiguous -> clarify,
governed questions -> proceed."""
from skills import input_skill as inputs
from workflows.investigation import run_investigation


def test_needs_clarification_on_anchorless_question():
    assert inputs.needs_clarification("why did it drop?") is not None
    assert inputs.needs_clarification("what happened?") is not None


def test_no_clarification_when_anchor_present():
    assert inputs.needs_clarification(
        "why did digital conversion drop yesterday") is None
    assert inputs.needs_clarification(
        "which categories had stockouts") is None


def test_pii_question_is_refused():
    t = run_investigation("why did orders drop for john.doe@example.com", use_index=False)
    a = t["answer"]
    assert a["intent"] == "refused"
    assert a.get("review") and a["review"]["risk_level"] == "high"
    assert a.get("table") is None  # no analysis performed


def test_ambiguous_question_asks_clarification():
    t = run_investigation("why did it drop?", use_index=False)
    assert t["answer"]["intent"] == "clarify"


def test_governed_question_proceeds():
    t = run_investigation(
        "Why did digital conversion drop yesterday compared with the prior 7-day average?",
        use_index=False)
    assert t["answer"]["intent"] == "overall"


def test_out_of_scope_question_is_not_a_conversion_dump():
    t = run_investigation("give me year over year order count", use_index=False)
    a = t["answer"]
    assert a["intent"] == "unsupported"
    assert not a.get("drivers") and not a.get("metrics") and a.get("table") is None
    assert a.get("review") is None
    assert "Digital conversion fell" not in a.get("headline", "")


def test_conversion_synonyms_route_to_overall():
    # broader synonyms: a decline framing about purchases still hits the flagship
    for q in ["why did sales drop yesterday", "why are fewer people buying?",
              "why are orders down vs last week"]:
        assert run_investigation(q, use_index=False)["answer"]["intent"] == "overall"


def test_listing_request_without_decline_is_out_of_scope():
    # a purchase noun without a decline framing is NOT a conversion question
    assert run_investigation("show me total order count", use_index=False)["answer"]["intent"] \
        == "unsupported"
