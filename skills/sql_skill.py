"""
Guardrail functions (Plan sections 12, 13, 18 / FR-05, FR-08, FR-10, FR-12).

Deterministic Python checks driven by guardrails.yaml:
  * SQL safety        : read-only SELECT over catalog-approved tables
  * Freshness/sync    : catalog/graph version + content_hash alignment
  * Source priority   : YAML > DuckDB > ChromaDB > NetworkX (LLM never decides)
  * Evidence gate     : score -> confidence label
  * Write protection  : refuse writes; convert to recommendation
"""
from __future__ import annotations

import re

from skills import catalog_skill as catalog


def _gr() -> dict:
    return catalog.load_catalog().get("sql_safety", {}) or {}


def _forbidden_pattern() -> re.Pattern:
    kws = catalog.load_catalog().get("sql_safety", {}).get(
        "forbidden_keywords",
        ["insert", "update", "delete", "drop", "alter", "create", "truncate",
         "replace", "merge", "grant", "attach", "copy", "pragma"])
    return re.compile(r"\b(" + "|".join(kws) + r")\b", re.IGNORECASE)


# scoring thresholds from guardrails.yaml (Plan section 11.1)
def _thresholds() -> dict:
    return catalog.load_catalog().get("confidence_thresholds", {
        "prune_below": 7, "likely_driver_at": 10, "max_score": 14})


PRUNE_BELOW = 7
LIKELY_AT = 10
MAX_SCORE = 14


def check_sql(sql: str) -> tuple[bool, str]:
    """(ok, reason). Read-only SELECT over approved tables only (FR-05)."""
    s = sql.strip().rstrip(";")
    if _forbidden_pattern().search(s):
        return False, "Blocked: write/DDL keyword detected. Prototype is read-only."
    if not re.match(r"^\s*(with|select)\b", s, re.IGNORECASE):
        return False, "Blocked: only SELECT/WITH statements are permitted."
    if ";" in s:
        return False, "Blocked: multiple statements are not allowed."
    referenced = set(re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w]*)", s, re.IGNORECASE))
    approved = {a.lower() for a in catalog.approved_tables()}
    cte_names = {c.lower() for c in re.findall(r"\b([a-zA-Z_]\w*)\s+AS\s*\(", s, re.IGNORECASE)}
    unknown = {t for t in referenced if t.lower() not in approved
               and t.lower() not in cte_names and len(t) > 2}
    if unknown:
        return False, f"Blocked: table(s) not approved in YAML catalog: {sorted(unknown)}"
    return True, "SELECT validated against approved tables."


def check_freshness(catalog_version: str, graph_version: str,
                    graph_hash: str | None = None) -> tuple[bool, str]:
    """Catalog sync/version gate (Plan section 7.2)."""
    if catalog_version != catalog.version():
        return False, "Stale: catalog version drift detected."
    if graph_version != catalog.version():
        return False, "Stale: graph version != catalog; rebuild required."
    if graph_hash is not None and graph_hash != catalog.content_hash():
        return False, "Stale: graph source hash != catalog content hash; rebuild required."
    return True, "Catalog, graph, and content hashes aligned."


def evidence_gate(score: int) -> str:
    """Map a branch score to a confidence label (Plan section 11.1)."""
    if score < PRUNE_BELOW:
        return "pruned"
    if score < LIKELY_AT:
        return "possible contributor"
    return "likely driver"


def overall_confidence(n_likely: int) -> str:
    return "high" if n_likely >= 1 else "inconclusive"


def refuse_write(user_text: str) -> str | None:
    """FR-12: never write to operational systems; convert to a recommendation."""
    if re.search(r"\b(update|set|change|push|write|delete|reorder|launch|send|increase|cut|adjust)\b",
                 user_text, re.IGNORECASE):
        return ("This prototype is read-only and cannot modify operational systems "
                "(ERP, OMS, CRM, pricing, campaign, inventory, fulfillment, service, "
                "finance). I can convert this into a human-reviewed recommendation "
                "routed to the responsible owner instead.")
    return None
