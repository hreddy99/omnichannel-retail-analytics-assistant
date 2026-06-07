# Omnichannel Retail Analytics Assistant

CMU capstone project — *Detailed Project Plan Updated Through Checkpoint 4.1*
(**ReAct + RAG + Knowledge Graph + Conditional Tree-of-Thought Beam Search**).

A **governed agentic research assistant** (not a chatbot) that investigates retail
performance questions — Phase I demo: *"Why did digital conversion drop yesterday
vs the prior 7-day average?"* — by grounding every answer in a governed catalog and
read-only query evidence before recommending action.

This repository is both an **interactive companion to the project plan** and a
**runnable prototype** of its architecture, using free, local, open-source tools.

## What it does

LangGraph controls a ReAct-style loop: **classify → catalog sync gate → retrieve
(ChromaDB) → validate (YAML) → relate (NetworkX) → baseline (DuckDB) → ToT gate →
beam search → evidence gate → synthesize**. The conditional Tree-of-Thought layer
(bounded beam search, width 2, depth 2) activates only when multiple driver paths
compete; it scores each branch on a 0–14 rubric, prunes weak paths, and keeps the
top two. Guardrails enforce read-only SQL, freshness/version sync, source-conflict
priority (YAML wins), and write refusal. Every step is recorded to an append-only
audit trail, and findings become **human-reviewed recommendations** — never writes.

A standout governance behavior: the ToT layer also proposes an *ungoverned*
hypothesis ("maybe prices rose?"). With no certified metric or approved table behind
it, the SQL validator blocks it and it is **pruned without spending query budget**.

## Quick start

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
python -m src.synthetic_data    # row counts per table
python -m src.data_validation   # Plan section 14.4 checks
```

## App pages

| Page | Contents |
|------|----------|
| 🏠 Overview | Executive summary, business roles, capstone fit, prototype status |
| ✅ Feasibility Review | Verdict, free/local stack, **implementation issues found & handled**, readiness checklist, risks |
| 🏗️ Architecture | LangGraph flow, live NetworkX graph, YAML files, agent roles, conflict rules |
| 🗺️ Step-by-Step Plan | Phase roadmap, 10 milestones with status, ToT model + rubric, tables, FR-01–FR-12 |
| 🔬 Live Demo | Runs the real pipeline; six tabs = the plan's four trace levels |
| 📄 Interactive Plan | Full plan section-by-section + downloadable `project_plan.html` |

The **Live Demo** exposes Plan section 17's four trace levels as tabs: Business
answer → Evidence → Trust details → ToT trace → Technical audit → Action log.

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
app.py                 Streamlit app (6 pages, multi-tab Live Demo)
build_html.py          Standalone interactive project_plan.html generator
requirements.txt       Free/local dependencies
catalog/               Split YAML catalog (source of truth)
  metrics.yaml tables.yaml drivers.yaml business_rules.yaml
  guardrails.yaml examples.yaml versions.yaml
src/
  synthetic_data.py    Faker fact_/dim_ generator + seeded scenarios + eval-only key
  data_validation.py   Plan section 14.4 validation checks
  catalog.py           Split-YAML loader, per-file hashes, governed chunks
  retrieval.py         ChromaDB + sentence-transformers (+ fallbacks) + sync gate
  graph.py             NetworkX graph from YAML (version + hash gated)
  guardrails.py        SQL safety / freshness / conflict / write refusal
  tot.py               Conditional ToT beam search (rubric, pruning, budget)
  workflow.py          LangGraph StateGraph controller (10 nodes)
  llm.py               Ollama wrapper with deterministic fallback
  audit.py             Append-only audit trail + action log (section 17.2)
  investigation.py     Orchestrator (public run_investigation entry point)
  plan_content.py      Structured plan content (shared by app + HTML)
```

## Safety & governance

Read-only on synthetic data; no PII. No writes to ERP, OMS, CRM, pricing, inventory,
campaign, fulfillment, service, or finance systems. Causality is labeled (*likely
driver / possible contributor / hypothesis / inconclusive*) and never overstated;
seeded expected outcomes are kept in an evaluation-only table the assistant never
reads during analysis.
