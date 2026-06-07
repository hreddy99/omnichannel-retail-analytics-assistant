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


@functools.lru_cache(maxsize=1)
def probe() -> dict:
    """Return {available, mode, detail}. Cached for the process."""
    try:
        import ollama
        models = ollama.Client().list().get("models", [])
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
            resp = ollama.Client().chat(model=info["model"],
                                        messages=[{"role": "user", "content": prompt}])
            return resp["message"]["content"].strip()
        except Exception:
            pass  # fall through to deterministic
    # deterministic fallback
    return (f"{headline} The evidence points to {driver_lines}. "
            f"Overall confidence is {confidence}; findings are routed to their owners "
            f"for human-reviewed follow-up rather than presented as proven root causes.")
