# AGENTS.md

Project-wide rules and the agent roster for the **Omnichannel Retail Analytics
Assistant** — a governed, read-only, multi-agent analytics assistant for a modern
data platform. Agents read the nearest `AGENTS.md` to the code they're editing.

## Project conventions
- **Language/stack:** Python 3.11–3.13. Free/local stack: Streamlit, LangGraph,
  DuckDB, ChromaDB, sentence-transformers, NetworkX, YAML, Ollama (optional).
- **Run it:** `python tools.py run` (or `setup` / `validate` / `doctor`).
- **Verify before commit:** `python -m evals.validation` (must all pass) and the
  `streamlit.testing.v1.AppTest` smoke checks; keep page renders at **0 exceptions**.
- **Read-only & governed:** no writes to operational systems; SELECT-only SQL over
  catalog-approved tables; YAML catalog is the source of truth; causality is labeled
  (likely driver / possible contributor / hypothesis / inconclusive), never asserted.
- **Keep this file lean** (≤150 lines); plain Markdown.

## Orchestration
The **Analytics Orchestrator** (LangGraph `StateGraph`, `workflows/graph.py`) routes a
question to one of three paths — conversion investigation, direct analytics insight,
or themed review — applies the query budget and stopping condition, and composes the
final answer. It dispatches the specialized analyst team **in parallel** only when a
cross-domain investigation is warranted.

## Support roles (in the workflow)
| Role | Responsibility | Tools |
|------|----------------|-------|
| Analytics Orchestrator | Routing, budget, stopping, synthesis | LangGraph |
| Semantic Agent | Retrieve certified definitions/templates; validate vs YAML | ChromaDB, YAML |
| Graph Reasoning Agent | metric → driver → table → owner relationships | NetworkX |
| Critic / Evaluator | Score branches 0–14, prune, beam-select (evidence gated on structure) | Guardrails, DuckDB |
| Synthesis + Exec Summary | Rank drivers; owner-routed recommendations | Result summaries, LLM (optional) |

## Specialized analyst team
Each analyst owns one domain, one governed driver, a scoped read-only toolset, and an
accountable owner. Full definitions (frontmatter `name` / `description` / `tools` +
instructions) live in [`agents/`](agents/):

| Analyst | Governed driver | Owner | Spec |
|---------|-----------------|-------|------|
| Marketing | `campaign_mix` | Marketing | [agents/marketing-analyst.md](agents/marketing-analyst.md) |
| Merchandising | `inventory_availability` | Merchandising | [agents/merchandising-analyst.md](agents/merchandising-analyst.md) |
| Fulfillment | `fulfillment_constraints` | Fulfillment Operations | [agents/fulfillment-analyst.md](agents/fulfillment-analyst.md) |
| Digital Analytics | `funnel_behavior` | Digital Analytics | [agents/digital-analytics-analyst.md](agents/digital-analytics-analyst.md) |
| Customer Service | `service_signal` | Customer Service | [agents/customer-service-analyst.md](agents/customer-service-analyst.md) |
| Finance | `finance_caveat` | Finance | [agents/finance-analyst.md](agents/finance-analyst.md) |
| Vendor / Category | `vendor_insight` | Merchandising | [agents/vendor-analyst.md](agents/vendor-analyst.md) |

Each runs in isolation (own DuckDB cursor, per-agent timeout); a failure degrades to an
excluded result without sinking the team. The roster and delegation/architecture flows
are rendered in-app on the **📐 Flow Diagrams** page.

> Note: these `agents/*.md` files document the *application's* analyst team in the
> standard `name`/`description`/`tools` + prompt convention. They are specifications,
> not Claude Code dev subagents (which live under `.claude/agents/`).
