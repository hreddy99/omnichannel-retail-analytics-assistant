# Multi-Agent System — Design Decisions

This document records *why* the Omnichannel Retail Analytics Assistant uses a
multi-agent design, *when* it does (and does not), and the trade-offs we
deliberately accept. Multi-agent systems unlock capability through
**specialization** and **parallelism**, but introduce **coordination overhead,
complexity, and new failure modes** — so the design is intentional, not default.

## The team

An **Orchestrator** (the LangGraph controller) coordinates the team. Work splits
into support roles and a parallel analyst team:

| Role | Type | Responsibility |
|------|------|----------------|
| Analytics Orchestrator | support | Routes the team, applies query budget + stopping. |
| Semantic Agent | support | Retrieves certified definitions/templates (ChromaDB) and validates vs YAML. |
| Graph Reasoning Agent | support | Maps metric → driver → table → owner (NetworkX). |
| Domain analysts (×N) | **parallel** | One analyst per domain; each runs one read-only DuckDB query and returns a finding + signal. |
| Critic / Evaluator | support | Scores each analyst's branch on the 0–14 rubric; prunes weak/ungoverned paths. |
| Synthesis Agent | support | Ranks supported drivers and writes the grounded answer. |
| Executive Summary Agent | support | Composes owner-routed recommended actions for leadership. |

### Specialized analysts

| Analyst | Domain | Governed driver |
|---------|--------|-----------------|
| Marketing | marketing | `campaign_mix` |
| Merchandising | merchandising | `inventory_availability` |
| Fulfillment | fulfillment | `fulfillment_constraints` |
| Digital Analytics | analytics | `funnel_behavior` |
| Customer Service | service | `service_signal` |
| Finance | finance | `finance_caveat` |
| Vendor / Category | merchandising | `vendor_insight` |

The app runs unified — the Orchestrator dispatches the full team every time and
the Critic decides what matters.

## Why multi-agent (the capability we want)

- **Specialization.** A conversion drop can come from campaigns, inventory,
  fulfillment, funnel, service, finance, or a vendor. Each domain needs its own
  table, certified metric, query pattern, and caveats. A dedicated agent
  encapsulates that expertise behind one uniform contract
  (`DomainAgent.analyze → AgentResult`).
- **Parallelism.** The domain investigations are independent, read-only queries,
  so they run concurrently (a bounded thread pool). The coordination log reports
  the measured wall-clock vs. sequential time and the resulting speedup.

## When we use the team — and when we don't

| Decision | Rationale |
|----------|-----------|
| Use the team | Cross-domain question and the ToT gate confirms competing drivers. |
| Use a single analyst | Narrow, single-domain question — no team, no coordination overhead. |
| Run analysts in parallel | Queries are independent and read-only. |
| Keep one central Critic | Uniform scoring standards across all specialists. |

## Trade-offs accepted (and mitigations)

| Trade-off | Mitigation |
|-----------|-----------|
| Coordination overhead | Bounded thread pool + fixed per-agent timeout; each agent makes exactly one read-only query. |
| Added complexity | One shared agent contract + one governed catalog → uniform, inspectable behavior. |
| New failure modes (slow / failing / disagreeing agents) | Each agent isolated (own DuckDB cursor, `try/except`, timeout). A failure degrades to an excluded result; the Critic + source-priority rules (DuckDB evidence and YAML win) resolve disagreement. |
| Non-determinism from parallelism | The Critic re-sorts deterministically (score, then evidence strength) — stable output regardless of completion order. |
| Observability gap | A coordination log records which agents ran, durations, speedup, and failures; every agent call is an audit event. |

## Failure handling, demonstrated

The Live Demo includes a "Simulate an agent failure" control. When an analyst is
forced to fail, the team **continues**: the failure is isolated, logged as a
degraded result, excluded by the Critic, and the remaining analysts still produce
a beam and an answer. This makes the new failure mode visible and proves the
mitigation.

## Where it lives in the code

- `src/agents.py` — `DomainAgent`, `AgentResult`, parallel `dispatch()`, the full
  analyst team, coordination log.
- `src/workflow.py` — `n_dispatch` (parallel team) and `n_critic` (scoring +
  beam) nodes in the LangGraph controller; `n_synthesize` adds owner-routed
  recommended actions and an executive summary.
- `src/tot.py` — per-domain evidence queries and the 0–14 scoring rubric.
- `src/investigation.py` — `run_investigation(..., inject_failure=)` and
  `run_investigation_stream(...)` for live step streaming.
