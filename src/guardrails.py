"""
Guardrail functions (Plan sections 4, 9, 10, 13 / FR-05, FR-09).

Custom Python checks - no external dependency. They enforce:
  * SQL safety        : only read-only SELECT over approved tables
  * Freshness         : catalog/graph version alignment
  * Evidence gate     : a branch must clear a score threshold to be a contributor
  * Write protection  : write requests are refused, never executed
"""
from __future__ import annotations

import re

from . import catalog

WRITE_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|replace|merge|grant|attach|copy|pragma)\b",
    re.IGNORECASE,
)

# Scoring thresholds from Plan section 8.
PRUNE_BELOW = 7        # branches scoring < 7 are pruned
LIKELY_AT = 10         # >= 10 may be ranked a likely driver
MAX_SCORE = 14         # sum of rubric maxima (2+2+2+3+2+2+1)


def check_sql(sql: str) -> tuple[bool, str]:
    """Return (ok, reason). Blocks anything that is not a read-only SELECT
    over catalog-approved tables (FR-05)."""
    s = sql.strip().rstrip(";")
    if WRITE_KEYWORDS.search(s):
        return False, "Blocked: write/DDL keyword detected. Prototype is read-only."
    if not re.match(r"^\s*(with|select)\b", s, re.IGNORECASE):
        return False, "Blocked: only SELECT/WITH statements are permitted."
    if ";" in s:
        return False, "Blocked: multiple statements are not allowed."
    referenced = set(re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w]*)", s, re.IGNORECASE))
    approved = catalog.approved_tables()
    unknown = {t for t in referenced if t.lower() not in {a.lower() for a in approved}}
    # allow CTE aliases (single letters / names defined via WITH)
    cte_names = set(re.findall(r"\b([a-zA-Z_]\w*)\s+AS\s*\(", s, re.IGNORECASE))
    unknown -= {c.lower() for c in cte_names}
    unknown -= {u for u in unknown if len(u) <= 2}
    if unknown:
        return False, f"Blocked: table(s) not approved in YAML catalog: {sorted(unknown)}"
    return True, "SELECT validated against approved tables."


def check_freshness(catalog_version: str, graph_version: str) -> tuple[bool, str]:
    if catalog_version != catalog.version():
        return False, "Stale: catalog version drift detected."
    if graph_version != catalog.version():
        return False, "Stale: graph version does not match catalog; rebuild required."
    return True, "Catalog and graph versions aligned."


def evidence_gate(score: int) -> str:
    """Map a branch score to a confidence label (Plan section 8)."""
    if score < PRUNE_BELOW:
        return "pruned"
    if score < LIKELY_AT:
        return "possible contributor"
    return "likely driver"


def refuse_write(user_text: str) -> str | None:
    """FR-09: never write to operational systems; convert to a recommendation."""
    if re.search(r"\b(update|set|change|push|write|delete|reorder|launch|send)\b",
                 user_text, re.IGNORECASE):
        return ("This prototype is read-only and cannot modify operational systems. "
                "I can turn this into a human-reviewed recommendation routed to the "
                "responsible owner instead.")
    return None
