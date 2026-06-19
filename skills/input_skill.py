"""
Input guardrails (Plan section 12.2 / Checkpoint 6 — input & scope checks).

Two deterministic, dependency-free checks applied to the RAW user question before
any retrieval or analysis:

  * detect_sensitive()    - the prototype runs only on synthetic/anonymized data.
                            If the user pastes real PII / private / proprietary data
                            (emails, phone, SSN, card numbers, or explicit cues), we
                            refuse and ask for synthetic input instead of analyzing it.
  * needs_clarification() - ambiguous / under-specified questions trigger a single
                            clarification (with the governed default offered) before
                            the assistant commits to an investigation.

Both return a user-facing message string when they fire, or None when the input is
clean. They are intentionally conservative so the governed scenario library and the
conversion-drop anchor are never mis-flagged.
"""
from __future__ import annotations

import re

# --- PII / sensitive-input patterns -------------------------------------------
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CARD = re.compile(r"\b(?:\d[ -]?){15,16}\b")
_PHONE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
# explicit cues that the user is bringing real/regulated data into a synthetic demo
_SENSITIVE_CUES = re.compile(
    r"\b(real customer|customer name|customer email|customer phone|home address|"
    r"employee (record|data|name)|social security|ssn|credit card|card number|"
    r"passport|date of birth|\bdob\b|patient|medical record|\bpii\b|personally identifiable|"
    r"proprietary|confidential|production (database|data|credentials)|api key|password)\b",
    re.IGNORECASE)

_SENSITIVE_MSG = (
    "This prototype runs only on synthetic, anonymized data and cannot accept real "
    "personal, private, proprietary, or regulated information (e.g. customer/employee "
    "details, emails, phone numbers, SSNs, or card numbers). Please remove the sensitive "
    "data and ask the question against the governed synthetic dataset instead. "
    "This request has been routed for governance review rather than analyzed."
)


def detect_sensitive(text: str) -> str | None:
    """Return a refusal message if the input appears to contain real PII / sensitive
    data, else None. Conservative: matches structured identifiers or explicit cues."""
    if not text:
        return None
    if (_EMAIL.search(text) or _SSN.search(text) or _CARD.search(text)
            or _PHONE.search(text) or _SENSITIVE_CUES.search(text)):
        return _SENSITIVE_MSG
    return None


# --- ambiguity / clarification ------------------------------------------------
# Governed "anchor" terms: if a question names at least one of these, it has enough
# signal to investigate. Mirrors the metrics/drivers/domains in the YAML catalog.
_ANCHOR_TERMS = (
    "conversion", "convert", "sales", "revenue", "gross", "net", "margin", "traffic",
    "session", "channel", "campaign", "paid", "social", "marketing", "ad", "spend", "budget",
    "inventory", "stock", "stockout", "availab", "category", "product", "merchand",
    "fulfil", "deliver", "shipping", "ship", "delay", "carrier", "region",
    "funnel", "cart", "checkout", "abandon", "browse",
    "contact", "service", "support", "complaint", "call",
    "finance", "reconcil", "return", "vendor", "partner", "supplier",
    "aov", "order", "device", "briefing", "risk", "trend", "review", "summary",
)
# Meta-intents the classifier already handles (actions / trust / caveats) — not ambiguous.
_META = re.compile(r"action|recommend|next step|definition|evidence path|grounding|"
                   r"caveat|freshness|confiden|reliab|trust this", re.IGNORECASE)

_CLARIFY_MSG = (
    "Your question is a bit broad for a governed investigation. Could you name the "
    "metric or area you mean — for example digital conversion, category sales, "
    "fulfillment delays, customer contacts, or finance reconciliation — and the time "
    "frame? If you'd like, I can default to **digital conversion vs the prior 7-day "
    "average**, the certified anchor metric."
)


def needs_clarification(question: str) -> str | None:
    """Return a clarification prompt for an under-specified question, else None.

    Fires only when the question carries no governed anchor term and is not a
    meta-question. Known scenario questions and the conversion anchor always pass.
    """
    if not question or not question.strip():
        return _CLARIFY_MSG
    q = question.lower()
    if _META.search(q):
        return None
    if any(term in q for term in _ANCHOR_TERMS):
        return None
    # Very short, anchorless inputs ("why did it drop?", "what happened?", "help")
    return _CLARIFY_MSG
