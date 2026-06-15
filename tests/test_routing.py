"""Routing contract: each question family is recognised by the right matcher."""
from app import content as P
from workflows import insights, themes
from workflows.graph import classify_intent


def test_anchor_question_is_overall():
    intent, _ = classify_intent(P.DEMO_QUESTIONS[0])
    assert intent == "overall"


def test_every_analytics_question_matches_an_insight():
    for q in insights.questions():
        assert insights.match(q) is not None
        # analytics questions are not themed reviews
        assert themes.match(q) is None


def test_every_theme_question_matches_a_theme():
    for q in themes.questions():
        assert themes.match(q) is not None
        assert insights.match(q) is None


def test_analytics_and_themed_are_disjoint_from_investigation():
    # a themed/analytics question should be caught before the investigation router
    for q in insights.questions() + themes.questions():
        assert insights.match(q) is not None or themes.match(q) is not None
