# Omnichannel Retail Analytics Assistant

CMU capstone project — *Updated Project Plan Through Checkpoint 4.1.*

A **governed investigation workflow** (not a general chatbot) that answers retail
performance questions — Phase I demo: *"Why did digital conversion drop yesterday
compared with the prior 7-day average?"* — by grounding every answer in a governed
catalog and read-only query evidence before recommending action.

This repository is both an **interactive companion to the project plan** and a
**runnable prototype** of its architecture. It runs entirely on a personal PC with
free, local, open-source tools — no paid cloud services, no enterprise data, no
production write access.

## What it does

For the demo question it: resolves a **certified metric definition** (YAML), checks
**freshness** of the knowledge layers, selects business relationships from a
**NetworkX graph**, runs **read-only DuckDB** queries over synthetic data, explores
competing driver hypotheses with a **conditional Tree-of-Thought beam search**
(width 2, depth 2), scores and prunes branches with a deterministic rubric, applies
**guardrails** (SQL safety, evidence gate, write-refusal), and produces an
**evidence-backed answer** with caveats, confidence, and owner routing.

A standout governance behavior: the ToT layer also proposes an *ungoverned*
hypothesis ("maybe prices rose?"). Because no certified metric or approved table
backs it, it is **pruned at the governance screen without spending query budget** —
the anti-hallucination story made concrete.

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints. No other services are required.

Generate the standalone interactive plan as HTML:

```bash
python build_html.py        # writes project_plan.html
```

## App pages

| Page | Contents |
|------|----------|
| 🏠 Overview | Executive summary, business problem, capstone-fit, prototype status |
| ✅ Feasibility Review | Feasibility verdict, free/local stack, required-vs-optional, risks |
| 🏗️ Architecture | LangGraph controller flow, live NetworkX graph, conflict rules, ToT rubric |
| 🗺️ Step-by-Step Plan | 8 milestones with status, functional requirements, seeded scenarios |
| 🔬 Live Demo | Runs the real workflow: evidence chart, reasoning trace, ToT scorecards, answer |
| 📄 Interactive Plan | Full plan section-by-section + downloadable `project_plan.html` |

## Architecture

```
Question → Classify/Retrieve → Validate vs YAML → Graph select →
  Conditional ToT beam search → SQL validate → DuckDB evidence →
    Evidence gate / stop → Grounded answer        (with revise/retry loop)
```

- **YAML catalog** (`catalog/catalog.yaml`) — the authoritative source of truth
  (metrics, tables, drivers, owners, SQL templates), versioned with a `content_hash`.
  Every other layer is validated against it; on conflict, **YAML wins**.
- **NetworkX graph** (`src/graph.py`) — generated from the catalog, version-stamped,
  blocked if stale.
- **DuckDB** (`src/synthetic_data.py`, `src/investigation.py`) — read-only analytics
  over fixed-seed synthetic data with four seeded anomalies.
- **Conditional ToT** (`src/investigation.py`) — bounded beam search with a 0–14
  scoring rubric; <7 pruned, 7–9 possible contributor, ≥10 likely driver.
- **Guardrails** (`src/guardrails.py`) — SQL validator (read-only SELECT over
  approved tables), freshness checks, evidence gate, write-request refusal.

## Repository layout

```
app.py                 Streamlit app (6 pages)
build_html.py          Standalone interactive project_plan.html generator
requirements.txt       Free/local dependencies
catalog/catalog.yaml   Governed semantic catalog (source of truth)
src/
  synthetic_data.py    Fixed-seed synthetic retail tables + seeded anomalies
  catalog.py           YAML loader, version/content_hash, ChromaDB-chunk modeling
  graph.py             NetworkX graph from YAML (freshness-gated)
  guardrails.py        SQL safety / freshness / evidence gate / write refusal
  investigation.py     LangGraph-style pipeline + conditional ToT beam search
  plan_content.py      Structured plan content (shared by app + HTML)
```

## Feasibility & optional components

The prototype runs with **zero external services**. The plan's optional enhancements
are documented but not required to run the demo:

- **Ollama** — local LLM for planning/drafting (a deterministic stand-in is used here).
- **ChromaDB + sentence-transformers** — vector retrieval (chunking is modeled in
  `catalog.chunks()` with version/`content_hash` metadata; embeddings are optional).
- **LangGraph** — orchestration (the deterministic pipeline mirrors the planned nodes).

## Safety

Read-only on synthetic data. No write operations. Weak causes are labeled *likely
driver / possible contributor / hypothesis / inconclusive* — causality is never
overstated, and write requests are refused and converted to human-reviewed
recommendations.
