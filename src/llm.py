"""
Local LLM wrapper (Plan section 5: Ollama).

Ollama is used for planning hints and response drafting. It is OPTIONAL: the
client probes for a running Ollama daemon at import; if none is reachable (e.g.
in a headless/cloud sandbox), the wrapper falls back to deterministic,
template-based text so the governed workflow still runs end-to-end. The LLM is
never a source of truth - all claims come from DuckDB evidence (Plan section 6).

The active mode ("ollama:<model>" or "deterministic-fallback") is surfaced in the
UI Trust/Audit panels so the degradation is visible, not hidden.
"""
from __future__ import annotations

import functools

DEFAULT_MODEL = "llama3.2"
# Keep the demo responsive: bound the request and cap generation so a slow local
# model (e.g. a 7B model on CPU) can't stall the investigation - it falls back to
# the deterministic template if it exceeds these limits.
REQUEST_TIMEOUT_S = 20.0
MAX_TOKENS = 200


@functools.lru_cache(maxsize=1)
def probe() -> dict:
    """Return {available, mode, detail}. Cached for the process."""
    try:
        import ollama
        models = ollama.Client(timeout=5).list().get("models", [])
        names = [m.get("model") or m.get("name") for m in models]
        model = DEFAULT_MODEL if any(DEFAULT_MODEL in (n or "") for n in names) else (
            names[0] if names else DEFAULT_MODEL)
        return {"available": True, "mode": f"ollama:{model}", "model": model,
                "detail": f"Ollama daemon reachable; using {model}."}
    except Exception as e:
        return {"available": False, "mode": "deterministic-fallback", "model": None,
                "detail": f"No Ollama daemon ({type(e).__name__}); using deterministic "
                          "template fallback. Start `ollama serve` on your PC to enable."}


def mode() -> str:
    return probe()["mode"]


def draft_answer(question: str, facts: str, confidence: str) -> str:
    """Answer the user's QUESTION in 2 cautious sentences using only `facts`.
    Uses Ollama if available (bounded by timeout + token cap), else returns the
    deterministic facts string. This keeps the response tuned to what was asked."""
    info = probe()
    if info["available"]:
        try:
            import ollama
            prompt = ("You are a retail analytics assistant. Answer the user's question in at most "
                      "2 cautious, business-facing sentences, using ONLY the facts provided. Do not "
                      "invent numbers. Address the question directly.\n"
                      f"Question: {question}\nFacts: {facts}\nOverall confidence: {confidence}.")
            resp = ollama.Client(timeout=REQUEST_TIMEOUT_S).chat(
                model=info["model"], messages=[{"role": "user", "content": prompt}],
                options={"num_predict": MAX_TOKENS})
            return resp["message"]["content"].strip()
        except Exception:
            pass
    return facts


def draft_summary(headline: str, drivers: list[dict], confidence: str) -> str:
    """Draft the business-facing summary. Uses Ollama if available, else a
    deterministic template (identical structure either way)."""
    info = probe()
    driver_lines = "; ".join(f"{d['label']} ({d['confidence']})" for d in drivers) or "no supported driver"
    if info["available"]:
        try:
            import ollama
            prompt = (
                "You are a retail analytics assistant. Write a 2-sentence, cautious, "
                "business-facing summary. Do not invent numbers beyond those given. "
                f"Headline: {headline}. Supported drivers: {driver_lines}. "
                f"Overall confidence: {confidence}. Use guarded language.")
            resp = ollama.Client(timeout=REQUEST_TIMEOUT_S).chat(
                model=info["model"], messages=[{"role": "user", "content": prompt}],
                options={"num_predict": MAX_TOKENS})
            return resp["message"]["content"].strip()
        except Exception:
            pass  # slow/unavailable -> fall through to deterministic
    # deterministic fallback
    return (f"{headline} The evidence points to {driver_lines}. "
            f"Overall confidence is {confidence}; findings are routed to their owners "
            f"for human-reviewed follow-up rather than presented as proven root causes.")
