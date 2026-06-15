"""
Audit trail + action log (Plan section 17.2).

Append-only, run-scoped event log capturing each workflow decision and tool call
with safe summaries (no raw sensitive data, no full result sets). Implemented
in-memory per run and serializable to JSONL/DuckDB. The action log converts
findings into human-reviewed recommendations - never operational writes
(Plan section 17.4, 18).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


@dataclass
class AuditLog:
    run_id: str = field(default_factory=lambda: dt.datetime.now().strftime("%Y-%m-%d-%H%M%S"))
    events: list[dict] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)

    def step(self, node: str, detail: str, ok: bool = True):
        """User-visible decision-log step (Plan section 17.3, level 1-2)."""
        self.steps.append({"node": node, "detail": detail, "ok": ok})

    def event(self, *, workflow_node: str, decision_type: str, tool_name: str = "",
              input_summary: str = "", output_summary: str = "",
              source_version_hash: str = "", score_or_confidence: str = "",
              status: str = "success", user_visible_note: str = "") -> dict:
        ev = {
            "run_id": self.run_id, "event_id": f"evt_{len(self.events) + 1:03d}",
            "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "workflow_node": workflow_node, "decision_type": decision_type,
            "tool_name": tool_name, "input_summary": input_summary,
            "output_summary": output_summary, "source_version_hash": source_version_hash,
            "score_or_confidence": score_or_confidence, "status": status,
            "user_visible_note": user_visible_note,
        }
        self.events.append(ev)
        return ev

    def action(self, *, owner: str, issue: str, evidence: str, confidence: str,
               priority: str, next_step: str):
        self.actions.append({
            "owner": owner, "issue": issue, "evidence": evidence, "confidence": confidence,
            "priority": priority, "recommended_next_step": next_step,
            "status": "recommended (human-reviewed; no system write)",
        })

    def to_jsonl(self) -> str:
        import json
        return "\n".join(json.dumps(e) for e in self.events)
