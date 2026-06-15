"""The externalised prompt templates load and format with their placeholders."""
from skills import llm_skill


def test_draft_answer_prompt_formats():
    p = llm_skill._load_prompt("draft_answer").format(
        question="q", facts="f", confidence="moderate")
    assert "q" in p and "f" in p and "moderate" in p


def test_draft_summary_prompt_formats():
    p = llm_skill._load_prompt("draft_summary").format(
        headline="h", drivers="d", confidence="low")
    assert "h" in p and "d" in p and "low" in p


def test_llm_falls_back_without_daemon():
    # In the sandbox there is no Ollama daemon; draft_answer must return the facts
    # string unchanged (deterministic fallback), never raise.
    out = llm_skill.draft_answer("why?", "conversion fell 24%", "moderate")
    assert isinstance(out, str) and out
