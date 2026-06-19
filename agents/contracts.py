"""
Typed agent-communication contracts.

Agents communicate through typed shared state, not free-form chat. Each agent
receives a scoped task (`AgentTask`) and returns a structured result
(`AgentFinding`); the Critic/ToT works in `BranchState`; every decision emits an
`AuditEvent`; and safety conditions raise a `HumanReviewRequest`. Keeping these
as dataclasses (rather than loose dicts) makes the contracts testable and lets a
run be replayed from the audit log.

These types mirror the structures the workflow already passes around
(AgentResult, the audit event dict, the ToT Branch) and provide the canonical,
documented schema for them plus light converters, so the contract is explicit
without changing runtime behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentTask:
    """Scoped task created by the Orchestrator for a domain agent.

    Never includes raw sensitive data — only governed identifiers and summaries.
    """
    run_id: str
    task_id: str
    agent_name: str
    metric_id: str
    date_range: str
    graph_path: list[str] = field(default_factory=list)
    allowed_tables: list[str] = field(default_factory=list)
    input_summary: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class AgentFinding:
    """Structured result returned by a domain agent and stored in workflow state."""
    task_id: str
    agent_name: str
    status: str               # ok | error | timeout
    evidence_summary: str
    caveats: str = ""
    confidence: str = ""
    owner: str = ""
    sql_template_id: str = ""
    row_count: int = 0
    freshness_status: str = "T-1 (yesterday)"

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class BranchState:
    """A single Tree-of-Thought branch as seen by ToT and the Critic."""
    branch_id: str
    driver: str
    depth: int
    evidence_plan: str
    source_version: str
    score: float
    keep_or_prune: str        # keep | prune
    reason: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class AuditEvent:
    """Append-only audit record for one workflow decision or tool call."""
    run_id: str
    event_id: str
    timestamp: str
    workflow_node: str
    tool_name: str
    decision_type: str
    input_summary: str = ""
    output_summary: str = ""
    status: str = "success"
    elapsed_ms: int = 0

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class HumanReviewRequest:
    """Raised when safety criteria require approval or escalation.

    The assistant only ever produces recommendations; this object records WHY a
    finding must be reviewed by its owner before any business action is taken.
    """
    run_id: str
    reason: str
    risk_level: str           # low | medium | high
    impacted_owner: str
    recommended_action: str
    evidence_summary: str = ""
    status: str = "pending review"

    def to_dict(self) -> dict:
        return self.__dict__.copy()


# Risk ordering helper for combining multiple triggers.
_RISK_RANK = {"low": 0, "medium": 1, "high": 2}


def max_risk(a: str, b: str) -> str:
    """Return the higher of two risk levels."""
    return a if _RISK_RANK.get(a, 0) >= _RISK_RANK.get(b, 0) else b
