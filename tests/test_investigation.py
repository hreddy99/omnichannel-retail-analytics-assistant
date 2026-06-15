"""End-to-end smoke: each question family runs and produces a sensible answer."""
from app import content as P
from workflows import insights, themes
from workflows.investigation import run_investigation


def test_conversion_investigation_runs():
    t = run_investigation(P.DEMO_QUESTIONS[0], use_index=False)
    ans = t["answer"]
    assert ans["intent"] == "overall"
    assert t.get("beam"), "expected at least one scored driver branch"
    assert ans.get("summary")


def test_analytics_question_runs():
    q = insights.questions()[0]
    t = run_investigation(q, use_index=False)
    assert t["answer"]["intent"] == "analytics"
    assert t["answer"].get("table") is not None


def test_themed_question_runs():
    q = themes.questions()[0]
    t = run_investigation(q, use_index=False)
    assert t["answer"]["intent"] == "themed"
    assert t["answer"].get("summary")
