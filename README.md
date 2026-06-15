# Omnichannel Retail Analytics Assistant

*Governed agentic analytics for the modern data platform*
(**ReAct + RAG + Knowledge Graph + Conditional Tree-of-Thought Beam Search**).

A **governed agentic analytics assistant** (not a chatbot) that investigates retail
performance questions — demo: *"Why did digital conversion drop yesterday
vs the prior 7-day average?"* — by grounding every answer in a governed catalog and
read-only query evidence before recommending action.

It represents a practical enterprise analytics pattern for agentic AI on top of a
governed modern data platform: the assistant sits above certified analytical data
products (curated Silver/Gold data) and turns natural-language questions into
governed analytical steps. This repository is both an **interactive product
overview** and a **runnable prototype** of its architecture, using free, local,
open-source tools.

## What it does

LangGraph controls a ReAct-style loop: **classify → catalog sync gate → retrieve
(ChromaDB) → validate (YAML) → relate (NetworkX) → baseline (DuckDB) → ToT gate →
dispatch multi-agent team (parallel) → critic + beam → evidence gate → synthesize**.
The conditional Tree-of-Thought layer (bounded beam search, width 2, depth 2)
activates only when multiple driver paths compete; the Critic scores each branch on
a 0–14 rubric, prunes weak paths, and keeps the top two. Guardrails enforce
read-only SQL, freshness/version sync, source-conflict priority (YAML wins), and
write refusal. Every step is recorded to an append-only audit trail, and findings
become **human-reviewed recommendations** — never writes.

### Multi-agent team

The domain investigations are run by a **team of specialized AI agents** dispatched
**in parallel** by an Orchestrator — a deliberate design (see
[`docs/multi_agent_design.md`](docs/multi_agent_design.md)):

- **Specialization** — one analyst per domain (Marketing, Merchandising,
  Fulfillment, Digital Analytics, Customer Service, Finance, and Vendor/Category,
  plus an Executive Summary agent), each owning its tables, certified metric, and
  guardrails.
- **Parallelism** — independent read-only queries run concurrently (bounded thread
  pool); the UI reports the measured wall-clock vs. sequential time and speedup.
- **Trade-offs handled** — coordination overhead (bounded pool + per-agent
  timeout), complexity (one shared agent contract + governed catalog), and new
  failure modes (each agent isolated; a failure degrades to an excluded result and
  the team continues). The Live Demo's "Simulate an agent failure" control shows
  this graceful degradation live.

The app runs **unified** — the full analyst team is dispatched on every
investigation. The **Multi-agent team** tab shows the roster, parallel timeline,
per-analyst findings, coordination metrics, and the design trade-offs.

A standout governance behavior: the ToT layer also proposes an *ungoverned*
hypothesis ("maybe prices rose?"). With no certified metric or approved table behind
it, the SQL validator blocks it and it is **pruned without spending query budget**.

## Quick start

**Option A — one command (recommended).** A stdlib-only task runner (`tools.py`)
creates the virtual environment, installs dependencies, validates the data, and
launches the app:

```bash
python tools.py            # setup + validate + launch  (http://localhost:8501)
```

Other subcommands:

```bash
python tools.py setup      # create .venv and install dependencies
python tools.py validate   # run the synthetic-data validation checks
python tools.py html       # generate the standalone project_plan.html
python tools.py run        # launch the Streamlit app (pass-through args, e.g. --server.port 8502)
python tools.py doctor     # print environment / tool status
```

**Option B — manual.**

```bash
pip install -r requirements.txt
streamlit run app.py
```

Generate the standalone interactive plan as HTML:

```bash
python build_html.py            # writes project_plan.html
```

Rebuild / validate the synthetic data:

```bash
python -m data.generator    # row counts per table
python -m evals.validation   # Plan section 14.4 checks
```

## App pages

| Page | Contents |
|------|----------|
| 🏠 Overview | Executive summary, business roles, enterprise/medallion alignment, capability alignment, status |
| ✅ Feasibility Review | Verdict, free/local stack, **implementation issues found & handled**, readiness checklist, risks |
| 🏗️ Architecture | LangGraph flow, live NetworkX graph, YAML files, agent roles, conflict rules |
| 🗺️ Step-by-Step Plan | Capability roadmap, milestones with status, ToT model + rubric, tables, FR-01–FR-12 |
| 🔬 Live Demo | Runs the real pipeline; live step trace + multi-agent team + four trace levels |
| 📄 Interactive Plan | Full plan section-by-section + downloadable `project_plan.html` |

The **Live Demo** streams each executing step, then exposes seven tabs: Business
answer → Multi-agent team → Evidence → Trust details → ToT trace → Technical audit
→ Action log.

## Free / local tool stack (Plan section 5)

| Layer | Tool | Notes |
|-------|------|-------|
| UI | Streamlit | multi-tab investigation view |
| Controller | **LangGraph** | real `StateGraph`, 10 nodes |
| Source of truth | YAML | split catalog + version manifest, per-file `content_hash` |
| Retrieval | **ChromaDB + sentence-transformers** | all-MiniLM-L6-v2; sync/version gate |
| Graph | NetworkX | metric/table/system/driver/owner, version+hash gated |
| Analysis | DuckDB | read-only SELECT over synthetic data |
| Data gen | **Faker** + numpy | fixed seed, no PII |
| LLM | Ollama (optional) | deterministic fallback if no daemon |
| Safety | Python guardrails | SQL validator, freshness, conflict, write refusal |

### Notes on optional components (with graceful, *visible* fallbacks)

- **Ollama** needs a running daemon + a pulled model — a one-time setup on a personal
  PC. If unreachable (e.g. a headless sandbox), the app uses deterministic,
  template-based drafting. The active mode is shown in **Trust details**.
- **sentence-transformers** downloads all-MiniLM-L6-v2 from huggingface.co. If that is
  unavailable, retrieval falls back to ChromaDB's bundled ONNX build of the **same
  model**, then to a deterministic hashing embedder, so it still runs offline.
- These fallbacks are surfaced in the UI, not hidden.

## Repository layout

```
build_html.py          Standalone interactive project_plan.html generator
tools.py               One-command setup / validate / run task runner
pyproject.toml         Package metadata + dependencies
requirements.txt       Free/local dependencies
.env.example           Optional local LLM (Ollama) configuration template

app/                   Streamlit UI
  main.py              Streamlit app (pages, multi-tab Live Demo)
  content.py           Structured plan content (shared by app + HTML)
  diagrams.py          Graphviz DOT diagrams rendered in-app
agents/                Multi-agent analyst team
  team.py              Specialized domain agents + parallel dispatch
  *.md                 Agent specs (frontmatter name/description/tools + prompt)
skills/                Governed capability wrappers (anatomy: <name>/SKILL.md)
  catalog_skill.py     Split-YAML loader, per-file hashes, governed chunks
  retrieval_skill.py   ChromaDB + sentence-transformers (+ fallbacks) + sync gate
  graph_skill.py       NetworkX graph from YAML (version + hash gated)
  sql_skill.py         SQL safety / freshness / conflict / write refusal
  tot_skill.py         Per-domain evidence queries + ToT beam-search scoring rubric
  audit_skill.py       Append-only audit trail + action log (section 17.2)
  ui_format_skill.py   Per-question chart resolution + business formatting
  llm_skill.py         Ollama wrapper with deterministic fallback
  spec_loader.py       Loads agent specs + SKILL.md anatomy for the UI
workflows/             LangGraph orchestration
  graph.py             LangGraph StateGraph controller (nodes + routing)
  investigation.py     Orchestrator (public run_investigation entry point)
  insights.py          11 standalone analytics questions
  themes.py            11 themed health / trend / risk reviews
data/                  Synthetic data
  generator.py         Faker fact_/dim_ generator + seeded scenarios + eval-only key
evals/                 Evaluation harness
  validation.py        Plan section 14.4 validation checks
catalog/               Split YAML catalog (source of truth)
  metrics.yaml tables.yaml drivers.yaml business_rules.yaml
  guardrails.yaml examples.yaml versions.yaml
prompts/               Structured prompt templates
scripts/               make_data / validate_catalog helpers
tests/                 Unit + UI-contract tests (pytest)
docs/                  Architecture notes + checkpoint documents
```

## Safety & governance

Read-only on synthetic data; no PII. No writes to ERP, OMS, CRM, pricing, inventory,
campaign, fulfillment, service, or finance systems. Causality is labeled (*likely
driver / possible contributor / hypothesis / inconclusive*) and never overstated;
seeded expected outcomes are kept in an evaluation-only table the assistant never
reads during analysis.
