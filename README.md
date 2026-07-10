# Conversational Analytics with Agentic AI

This project demonstrates a governed agentic AI approach to conversational analytics, where business users can ask natural language questions and receive evidence-backed answers from trusted data.

Watch the demo:
Conversational Analytics with Agentic AI | DataToAgents Demo
https://www.youtube.com/watch?v=JBJLkgZHbFw&t=313s


# Omnichannel Retail Analytics Assistant

**A governed conversational-analytics investigation layer for enterprise retail.**

A business user asks a plain-English retail question over scattered, multi-domain data and gets
back an **evidence-backed, owner-routed answer**, with caveats, confidence, and a full audit
trail, in seconds. It is a runnable prototype, not a chatbot: an LLM, a vector database, a
knowledge graph, and read-only analytical tools work together under enforced governance.

BI tools (Power BI, Databricks AI/BI) are strong for dashboards, semantic-model Q&A, and
text-to-SQL, but complex retail questions need more than a single chart or one-shot answer. This
project shows how conversational analytics can evolve into a governed, multi-step investigation
that **complements BI rather than replacing it**, adding the workflow that turns
*"what happened?"* into *"why, with evidence, confidence, caveats, and an accountable owner."*

## The problem

Retail leaders ask simple-sounding questions that are expensive to answer:

- Why did digital conversion drop yesterday?
- Which categories have high traffic but weak conversion?
- Are delivery delays increasing customer-service contacts?
- Why do ecommerce sales not reconcile with finance revenue?

The evidence is scattered across clickstream, orders, inventory, fulfillment, campaign,
customer-service, finance, product, category, and vendor systems. Teams spend hours or days
pulling extracts, reconciling metric definitions, debating root causes, and validating
assumptions before leaders can act. A prompt-only LLM isn't reliable enough: it can invent
definitions, ignore table grain, miss freshness caveats, or assert a cause the evidence doesn't
support.

## How it works

The assistant runs a multi-step investigation as an explicit, auditable **LangGraph** state
machine:

```
classify → catalog sync gate → retrieve (ChromaDB) → validate (YAML) → relate (NetworkX)
→ baseline (DuckDB) → ToT gate → dispatch multi-agent team (parallel) → critic + beam
→ evidence gate → synthesize
```

- **YAML** is the certified source of truth for metrics, tables, joins, owners, freshness, and
  guardrails.
- **ChromaDB** retrieves only approved context; **NetworkX** maps metric → driver → table → owner.
- **DuckDB** runs read-only queries over synthetic Silver/Gold-style data.
- A **multi-agent team** of specialized analysts (Marketing, Merchandising, Fulfillment, Digital
  Analytics, Customer Service, Finance, Vendor/Category) is dispatched in parallel; a failing
  analyst degrades gracefully (isolated, logged, excluded, and the team continues).
- A conditional **Tree-of-Thought** layer (bounded beam search, width 2, depth 2) activates only
  when driver paths compete: a Critic scores each branch on a 0 to 14 rubric, prunes
  weak or ungoverned paths, and **escalates genuine ties instead of forcing a root cause**.
- **Ollama/qwen2.5** drafts the final wording only. It never controls truth, SQL execution,
  evidence, or safety, and its draft is used only if it preserves every figure exactly.

Design rationale: [`docs/multi_agent_design.md`](docs/multi_agent_design.md).

## Requirements

| Resource | Recommended | Minimum | Notes |
|----------|-------------|---------|-------|
| RAM | 16 GB | 8 GB | ≥ 10 GB pulls `qwen2.5:7b`; below that, setup pulls the smaller `qwen2.5:3b`. |
| Disk | ~8 GB free | ~4 GB | PyTorch plus the embedding model plus the Ollama model. |
| CPU | 4+ cores | 2 cores | Generation runs on CPU; a GPU is optional and auto-used by Ollama if present. |
| OS | macOS / Linux / Windows | Any | Python 3.11+. No paid cloud services. |

## Setup & run

**One command (recommended).** The stdlib-only task runner `tools.py` creates the virtual
environment, installs the Python dependencies **and** the Ollama LLM (detects your RAM, installs
Ollama, starts the daemon, pulls the right model), validates the data, and launches the app at
<http://localhost:8501>:

```bash
python tools.py                 # setup + validate + launch
python tools.py --skip-ollama   # skip the Ollama install (CI / headless)
```

Individual steps:

```bash
python tools.py setup      # create .venv and install dependencies
python tools.py validate   # run the synthetic-data validation checks
python tools.py run        # launch the app (pass-through args, e.g. --server.port 8502)
python tools.py doctor     # print RAM / CPU / model / Ollama daemon status
```

**Manual.**

```bash
pip install -r requirements.txt
streamlit run app/main.py
```

## Usage

The app has five pages:

| Page | What it shows |
|------|---------------|
| 🏠 Overview | What the project is, the problem, system goal & scope, business roles |
| 🏗️ Architecture | Reference diagrams, LangGraph flow, live NetworkX graph, agent roster |
| 📚 Data Catalog | The 18 governed tables, certified metrics, drivers, and the knowledge graph |
| 🔬 Run Analysis | Runs the real pipeline; live step trace plus multi-agent team plus seven review tabs |
| 🧪 Evaluation & Safety | Grouped pass/fail harness with live results and latency |

Start on **Run Analysis**: pick a question and watch each step execute, then explore the seven
tabs (Business answer → Multi-agent team → Evidence → Trust details → ToT trace → Technical
audit → Action log). The question picker covers the flagship conversion investigation, three
cross-functional executive briefings, 13 direct analytics questions, and 12 themed health, trend,
and risk reviews.

## Scope

This is a local capstone prototype with synthetic fixed-seed data. It is not a production
deployment, and not a replacement for Power BI, Databricks AI/BI, or an enterprise semantic
layer. In production, the same pattern sits on top of a governed data platform and semantic
layer, reading certified Silver/Gold data products or governed read-in-place federation (e.g.,
Lakehouse Federation / Unity Catalog foreign catalogs, Trino), with RBAC, lineage, freshness
checks, data-quality monitoring, and human-approved action routing. **The key requirement is
governance, not physical data location.**

## Repository layout

```
tools.py     One-command setup / validate / run task runner
app/         Streamlit UI (5 pages; main.py, content.py)
agents/      Multi-agent analyst team (team.py plus agent specs)
skills/      Governed capability wrappers (catalog, retrieval, graph, SQL, input,
             ToT scoring, audit, UI format, LLM, spec loader)
workflows/   LangGraph orchestration (graph.py, investigation.py, insights.py, themes.py)
data/        Synthetic data generator (Faker, fixed seed, eval-only key)
evals/       validation.py plus safety_suite.py harnesses
catalog/     Split YAML catalog (source of truth)
docs/        Design notes and architecture diagrams
```
