"""
Multi-agent analyst team.

WHY MULTI-AGENT, DELIBERATE DESIGN DECISIONS
---------------------------------------------
A conversion drop can stem from several domains at once (campaigns, inventory,
fulfillment, funnel, service, finance, vendor). Investigating them is:
  * SPECIALIZED  - each domain needs its own table, metric, and read pattern; a
                   dedicated agent encapsulates that expertise and its guardrails.
  * PARALLELIZABLE - the domain investigations are independent read-only queries,
                   so they run concurrently, cutting wall-clock latency.

So the domain analysts are modeled as a *team* of specialized agents dispatched
in parallel by an Orchestrator, with a Critic scoring their findings and a
Synthesizer composing the answer. This is a deliberate choice, not multi-agent
for its own sake:

WHEN WE USE MULTIPLE AGENTS
  - Only when the question is cross-domain (the ToT gate confirms competing
    drivers). A narrow, single-domain question uses one analyst - no team.
  - The specialized analysts whose domain is relevant are dispatched
    (specialization keeps each analyst focused).

TRADE-OFFS WE ACCEPT (and how we mitigate them)
  - Coordination overhead: a thread pool + a fixed per-agent timeout bound it;
    each agent does exactly ONE read-only query.
  - Complexity: agents share one contract (DomainAgent.analyze -> AgentResult)
    and one governed catalog, so behavior stays uniform and inspectable.
  - New failure modes: a slow/failing agent must not sink the team. Each agent
    is isolated (own DuckDB cursor, try/except, timeout); failures degrade to an
    'error'/'timeout' result that the Critic simply excludes. The coordination
    log records what ran, how long, and what failed - full observability.
  - Non-determinism from parallelism: results are re-sorted deterministically by
    the Critic (score, then evidence strength), so output order is stable.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from skills import catalog_skill as catalog, tot_skill as tot

# driver key -> human-facing analyst name
AGENT_NAMES = {
    "campaign_mix": "Marketing Analyst",
    "inventory_availability": "Merchandising Analyst",
    "fulfillment_constraints": "Fulfillment Analyst",
    "funnel_behavior": "Digital Analytics Analyst",
    "service_signal": "Customer Service Analyst",
    "finance_caveat": "Finance Analyst",
    "vendor_insight": "Vendor / Category Analyst",
}

# The full specialized analyst team. The app runs unified - the whole team is
# dispatched every investigation; the Orchestrator/Critic decide what matters.
ANALYSTS = ["campaign_mix", "inventory_availability", "fulfillment_constraints",
            "funnel_behavior", "service_signal", "finance_caveat", "vendor_insight"]

# Non-domain team members (represented in the workflow nodes), shown in the roster.
SUPPORT_ROLES = [
    ("Analytics Orchestrator", "Routes the team, applies query budget and stopping."),
    ("Semantic Agent", "Retrieves certified definitions/templates from ChromaDB and validates vs YAML."),
    ("Graph Reasoning Agent", "Maps metric -> driver -> table -> owner via NetworkX."),
    ("Critic / Evaluator", "Scores each analyst's branch on the 0-14 rubric; prunes weak paths."),
    ("Synthesis Agent", "Ranks supported drivers and writes the grounded business answer."),
    ("Executive Summary Agent", "Composes owner-routed recommended actions for leadership."),
]

PER_AGENT_TIMEOUT_S = 12.0
MAX_WORKERS = 6


@dataclass
class AgentResult:
    key: str
    agent_name: str
    domain: str
    owner: str
    finding: str = ""
    signal: float = 0.0
    sql: str = ""
    evidence: Any = None
    status: str = "ok"          # ok | error | timeout
    elapsed_ms: int = 0
    error: str = ""
    retries: int = 0            # targeted retries attempted before giving up

    def to_finding(self, task_id: str = "", confidence: str = "") -> "AgentFinding":
        """Project this result onto the typed AgentFinding contract."""
        from agents.contracts import AgentFinding
        rows = 0
        try:
            rows = int(len(self.evidence)) if self.evidence is not None else 0
        except TypeError:
            rows = 0
        return AgentFinding(
            task_id=task_id or self.key, agent_name=self.agent_name, status=self.status,
            evidence_summary=self.finding, confidence=confidence, owner=self.owner,
            sql_template_id=self.key, row_count=rows)


class DomainAgent:
    """A specialized analyst: one domain, one governed driver, one read-only query."""

    def __init__(self, key: str):
        drv = catalog.get_driver(key) or {}
        self.key = key
        self.name = AGENT_NAMES.get(key, key)
        self.domain = drv.get("domain", "")
        self.owner = drv.get("owner", "")

    def analyze(self, con, meta: dict) -> AgentResult:
        td, b0, b1 = meta["target_day"], meta["baseline_start"], meta["baseline_end"]
        res = AgentResult(self.key, self.name, self.domain, self.owner)
        t0 = time.perf_counter()
        try:
            cur = con.cursor()  # thread-safe concurrent read off the same database
            sql, ev, signal, finding = tot.DRIVER_QUERY[self.key](cur, td, b0, b1)
            res.sql, res.evidence, res.signal, res.finding = sql, ev, signal, finding
        except Exception as e:  # isolate failure - the team continues
            res.status = "error"
            res.error = f"{type(e).__name__}: {e}"
            res.finding = "Agent failed; excluded from synthesis."
        res.elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return res


def analyst_team() -> list[DomainAgent]:
    """The full specialized analyst team (unified)."""
    return [DomainAgent(k) for k in ANALYSTS]


def dispatch(agents: list[DomainAgent], con, meta: dict,
             inject_failure: str | None = None) -> tuple[list[AgentResult], dict]:
    """Run the domain analysts IN PARALLEL. Returns (results, coordination_log).

    inject_failure: optional agent key forced to raise, to demonstrate that a
    single agent failure degrades gracefully without sinking the team.
    """
    results: list[AgentResult] = []
    timeline: list[dict] = []
    wall_t0 = time.perf_counter()

    def _wrapped(agent: DomainAgent) -> AgentResult:
        # A genuine failure gets ONE targeted retry before the team gives up and
        # escalates it as degraded (Checkpoint 6: retry once, then human review).
        if inject_failure and agent.key == inject_failure:
            r = AgentResult(agent.key, agent.name, agent.domain, agent.owner)
            r.status = "error"; r.error = "Injected failure (demo), retried once, still failing"
            r.retries = 1
            r.finding = "Agent failed after 1 retry; excluded from synthesis."
            return r
        r = agent.analyze(con, meta)
        if r.status != "ok":            # transient failure → one repair/retry
            r = agent.analyze(con, meta)
            r.retries = 1
        return r

    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(agents) or 1)) as pool:
        futures = {pool.submit(_wrapped, a): a for a in agents}
        for fut in as_completed(futures):
            a = futures[fut]
            try:
                results.append(fut.result(timeout=PER_AGENT_TIMEOUT_S))
            except Exception as e:
                r = AgentResult(a.key, a.name, a.domain, a.owner)
                r.status = "timeout" if "Timeout" in type(e).__name__ else "error"
                r.error = f"{type(e).__name__}: {e}"
                r.finding = "Agent did not return in time; excluded from synthesis."
                results.append(r)

    wall_ms = int((time.perf_counter() - wall_t0) * 1000)
    sum_ms = sum(r.elapsed_ms for r in results)
    for r in results:
        timeline.append({"agent": r.agent_name, "domain": r.domain, "status": r.status,
                         "elapsed_ms": r.elapsed_ms, "error": r.error})
    timeline.sort(key=lambda x: x["agent"])
    coord = {
        "n_agents": len(agents),
        "n_ok": sum(1 for r in results if r.status == "ok"),
        "n_failed": sum(1 for r in results if r.status != "ok"),
        "wall_ms": wall_ms,                       # parallel wall-clock
        "sequential_ms": sum_ms,                  # if run one-by-one
        "speedup": round(sum_ms / wall_ms, 2) if wall_ms else 1.0,
        "retries": sum(getattr(r, "retries", 0) for r in results),
        "timeline": timeline,
    }
    return results, coord
