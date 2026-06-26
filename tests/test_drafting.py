"""LLM draft hygiene: markdown artifacts are stripped, and a reworded draft is only
accepted if it preserves every figure verbatim — otherwise we fall back to the
deterministic facts (so a governed numeric summary is never mangled)."""
from skills.llm_skill import _sanitize_draft, _preserves_facts

FACTS = ("Conversion 3.66%; net revenue $92,591 (gross $105,513, returns $7,417); "
         "118 support contacts; slowest region west (regional) at 3.9d delay.")


def test_sanitize_strips_markdown():
    assert "`" not in _sanitize_draft("net revenue of `92,591 from gross sales of` 105,513")
    assert "*" not in _sanitize_draft("**bold** and *italic* text")


def test_garbled_draft_is_rejected():
    # the real failure: backticked code span + dropped '$' on revenue/gross
    bad = ("Today's conversion rate is 3.66%, with net revenue of `92,591 from gross sales "
           "of` 105,513 after accounting for returns of $7,417.")
    assert _preserves_facts(_sanitize_draft(bad), FACTS) is False


def test_faithful_reword_is_accepted():
    good = ("Conversion was 3.66%; net revenue $92,591 on gross $105,513 (returns $7,417); "
            "118 support contacts; slowest region west at 3.9d.")
    assert _preserves_facts(_sanitize_draft(good), FACTS) is True
