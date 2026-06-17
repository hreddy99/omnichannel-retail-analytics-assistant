# Code Walkthrough — following one question through the system

**Audience:** anyone reviewing this capstone who wants to understand *how* it works and *which
concepts from the program it demonstrates* — explained in plain language, no jargon assumed.

**The trick to understanding any system:** don't read it file-by-file. Follow one request from the
moment it's typed to the moment an answer comes back. We'll trace this one question:

> *"Why did digital conversion drop yesterday compared with the prior 7-day average?"*

Each stop on the journey is a real concept you learned in the program. Here's the map, then the story.

---

## Concept → where it lives (the cheat sheet)

| # | Concept from the program | Plain-English version | Code |
|---|---|---|---|
| 1 | Modern data platform / **medallion architecture** | Where the data lives and how it's layered | `data/generator.py` |
| 2 | **Data governance / semantic layer** | One official rulebook of metrics & tables | `catalog/*.yaml`, `skills/catalog_skill.py` |
| 3 | **Guardrails / responsible AI** | Hard safety rules the AI can't break | `skills/sql_skill.py` |
| 4 | **RAG** (retrieval-augmented generation) + embeddings | Look up the right facts before answering | `skills/retrieval_skill.py` |
| 5 | **Knowledge graph** reasoning | A map of what relates to what (and who owns it) | `skills/graph_skill.py` |
| 6 | **Agent orchestration / state machine** (LangGraph, ReAct) | The conductor that runs the steps in order | `workflows/graph.py` |
| 7 | **Multi-agent systems** | A team of specialists working in parallel | `agents/team.py`, `agents/contracts.py` |
| 8 | **Tree-of-Thoughts + beam search + scoring** | Test several explanations, keep the best | `skills/tot_skill.py` |
| 9 | **LLM grounding & graceful degradation** | The language model writes prose only, never facts | `skills/llm_skill.py` |
| 10 | **Human-in-the-loop + causal humility** | Recommend, don't act; say "likely," not "caused" | `workflows/graph.py` (review/synthesize) |
| 11 | **Observability / lineage / audit** | A black-box recorder for every decision | `skills/audit_skill.py` |
| 12 | **Evaluation & reproducibility** | Prove it works, the same way every time | `evals/validation.py`, `tests/` |
| 13 | **Progressive disclosure UX** | Same answer at 4 depths for 4 audiences | `app/main.py` |

The entry point that ties it all together is `workflows/investigation.py → run_investigation()`.

---

## The journey

### Stop 1 — The data and where it lives  ·  *medallion architecture*
**File:** `data/generator.py`

**Common-sense version:** before you can analyze a store, you need a store. This file builds a
realistic-but-fake retail business in memory (an in-process database called DuckDB) — sessions,
orders, inventory, fulfillment, contacts, finance, vendors: **18 tables**. It's organized the way real
companies organize data — the *medallion* pattern: raw events (**Bronze**) → clean fact/dimension
tables (**Silver**) → business-ready metrics (**Gold**).

**The clever part:** it seeds a *known story*. Yesterday's conversion is deliberately ~23% lower than
normal, and that drop has consistent causes baked in (a paid-social traffic shift, a category
stockout, regional delivery delays). Because we *planted* the answer, we can later check the system
*finds* it — that's what makes evaluation possible. A fixed random seed means the same world is built
every time, so results are reproducible.

> **Point at:** `build_duckdb()` (builds the world), `get_meta()` (which day is "yesterday"), and the
> seeded scenario knobs near the top. The finance table even models *gross-to-net* correctly (net is
> below gross after returns/discounts) — a real accounting concept.

---

### Stop 2 — The rulebook  ·  *data governance / semantic layer*
**Files:** `catalog/metrics.yaml`, `tables.yaml`, `drivers.yaml`, `guardrails.yaml`, …  ·  read by `skills/catalog_skill.py`

**Common-sense version:** the #1 reason two analysts get two different "conversion rates" is that they
quietly used two different definitions. So this project keeps a single **official rulebook** in plain
YAML files: every metric's exact definition, which tables are allowed, which "drivers" can explain a
change, who owns each, and the safety rules. **Nothing else is allowed to invent a definition.**

This is the *semantic layer* / governance concept: the business meaning lives in one versioned,
inspectable place — not buried in code or a prompt. `catalog_skill.py` loads it and, importantly,
computes a **content hash** (`content_hash()`) — a fingerprint of the rulebook. If the rulebook
changes, the fingerprint changes, and everything downstream can detect it.

> **Point at:** `metrics.yaml` (a certified definition with owner + caveats), `approved_tables()`, and
> `version()` / `content_hash()`. This file *is* the "single source of truth" you hear about.

---

### Stop 3 — The safety rules  ·  *guardrails / responsible AI*
**File:** `skills/sql_skill.py`

**Common-sense version:** an AI that can run any database command is dangerous. So before *any* query
runs, it passes through a bouncer. `check_sql()` enforces three hard rules: (1) **read-only** — only
`SELECT`/`WITH`, never insert/update/delete/drop; (2) **approved tables only** — every table named
must be in the rulebook; (3) **one statement only**. Fail any rule → the query is *blocked before it
executes*.

`refuse_write()` is the same idea for the user: if you ask it to "update the budget," it politely
refuses and offers a *recommendation* instead. This is the difference between governance that's
**enforced in code** versus a polite request in a prompt that a model can ignore.

> **Point at:** `check_sql()` (the bouncer) and `refuse_write()` (the read-only promise). In the demo,
> typing "update the paid-social budget" triggers `refuse_write` — always a crowd-pleaser.

---

### Stop 4 — Looking up the right facts  ·  *RAG + embeddings*
**File:** `skills/retrieval_skill.py`

**Common-sense version:** when the question arrives, the system first *looks things up* rather than
guessing — exactly like RAG (retrieval-augmented generation). Each entry in the rulebook is turned
into a vector (a list of numbers that captures meaning) and stored in a local vector database
(ChromaDB). The question is turned into a vector too, and we fetch the **top-k closest** entries —
the certified definitions and tables most relevant to "conversion drop."

Two mature touches: (a) **graceful fallback** — it prefers a real embedding model
(`all-MiniLM-L6-v2`), but if that can't load offline it falls back to a deterministic hashing
embedder so the demo *always* runs; (b) the **sync gate** — each retrieved chunk carries the rulebook
fingerprint it was built from; if that no longer matches the current rulebook, the chunk is flagged
*stale* and rejected. Retrieval can't quietly serve outdated definitions.

> **Point at:** `retrieve()` (top-k + the `validated`/`fresh` flags), `_exists_in_yaml()` (double-check
> the hit against the rulebook), and `_pick_embedder()` (the offline fallback ladder).

---

### Stop 5 — The map of relationships  ·  *knowledge graph*
**File:** `skills/graph_skill.py`

**Common-sense version:** facts alone aren't enough; you need to know how things *connect*. This builds
a graph (with NetworkX) straight from the rulebook: a metric is *measured_by* certain tables, is
*affected_by* certain drivers, each driver *uses* tables and is *owned_by* a team. So from "conversion"
the system can walk the map to "which drivers could explain this, which tables prove it, and **which
team owns the fix**."

The governance theme repeats here: the graph is stamped with the rulebook version, and if it's out of
date, traversal is **blocked** until it's rebuilt — the graph is always subordinate to the YAML rulebook.

> **Point at:** `build_graph()` (edges = relationships) and `driver_path()` (returns the tables + owner
> for a driver, or `None` if stale). This is how an answer always comes with an accountable owner.

---

### Stop 6 — The conductor  ·  *agent orchestration / state machine (LangGraph)*
**Files:** `workflows/investigation.py` (entry) → `workflows/graph.py` (the machine)

**Common-sense version:** something has to run all these steps in the right order and carry the
results forward. That's a **state machine** built with LangGraph — think of an assembly line where each
station does one job and passes the work along. The shared clipboard is `WState`. The line is:

> classify → sync-check → retrieve → validate → relate (graph) → measure baseline → **decide if we need
> the team** → dispatch the team → critique & rank → evidence gate → human review → write the answer.

The very first station, `classify_intent()`, is smart routing: a narrow question ("how did paid social
do?") is sent down a short path with **one** analyst; a broad question ("why did conversion drop?" or
"brief me across the business") triggers the **full team**. This is the ReAct idea — reason about what
kind of question it is, then act accordingly — and it's where we avoid "multi-agent for its own sake."

> **Point at:** `build_workflow()` (the assembly line wired up), `classify_intent()` (the router), and
> notice every station calls `_step(...)` so the user can watch it happen live.

---

### Stop 7 — The team of specialists  ·  *multi-agent systems*
**Files:** `agents/team.py`, `agents/contracts.py`

**Common-sense version:** a conversion drop usually has *several* causes at once across *different*
departments. One generalist is slow and shallow; instead we dispatch **seven specialist analysts**
(Marketing, Merchandising, Fulfillment, Digital, Service, Finance, Vendor) — each runs **one read-only
query in its own lane**, and they run **in parallel** (a thread pool) to save time.

The grown-up engineering is in the trade-offs: each agent has its **own database cursor**, a **timeout**,
and a `try/except`, so a slow or failing agent is **isolated and excluded** — it can't sink the team.
And they don't chat in free text; they communicate through **typed contracts** (`AgentTask` in,
`AgentFinding` out, in `contracts.py`) so the hand-offs are structured, testable, and replayable.

> **Point at:** `ANALYSTS` (the roster), `dispatch()` (the parallel run + the coordination log showing
> the speedup and any failures), and `DomainAgent.analyze()` (one agent, one governed query).

---

### Stop 8 — Weighing the explanations  ·  *Tree-of-Thoughts + beam search + scoring*
**File:** `skills/tot_skill.py`

**Common-sense version:** now we have several candidate explanations ("branches"). Which do we trust?
Each branch is scored on a transparent **0–14 rubric**: Is the metric in the rulebook? Is there an
approved graph path? Did the SQL pass the bouncer? **How strong is the actual evidence?** Is the data
fresh? Is it business-relevant with an owner? (`score_branch()`).

Two ideas from the program show up here:
- **Beam search** — keep only the top few branches (`BEAM_WIDTH = 2`) instead of chasing every idea;
  it bounds the cost (`QUERY_BUDGET = 5`). Weak branches are *pruned*.
- **Governance can't be overpowered** — evidence strength only counts *if* the structural checks pass
  first (`STRUCTURAL_MIN`). So a branch with dramatic numbers but no certified metric **cannot** win.

There's even a planted **ungoverned hypothesis** ("maybe prices rose?") with no approved table —
`ungoverned_branch()` — and the system *prunes it without spending budget*, proving the guardrails work.
The score converts to a plain label via `evidence_gate()`: *pruned* / *possible contributor* /
*likely driver*.

> **Point at:** `score_branch()` (the rubric), `BEAM_WIDTH`/`QUERY_BUDGET` (the bounded search), and
> `ungoverned_branch()` (the trap that gets caught).

---

### Stop 9 — Writing it in English  ·  *LLM grounding & graceful degradation*
**File:** `skills/llm_skill.py`

**Common-sense version:** here's the part people expect to be "the AI" — and it's deliberately the most
*restrained* piece. The language model (a local one via Ollama) is handed the **already-proven facts**
and asked only to phrase them in two cautious sentences (`draft_answer()`). It is **never** a source of
numbers or definitions. If no model is running, a deterministic template writes the same prose — so the
**facts are identical either way** and the demo can't break. The active mode is shown in the UI, so any
degradation is visible, not hidden.

This is the core responsible-AI stance: **the LLM is on a short leash.** All truth comes from governed
SQL over certified metrics; the model just makes it readable.

> **Point at:** `draft_answer()` (facts in → prose out) and `probe()` (detects the model, falls back
> cleanly). Say clearly: "the model can't invent a number here even if it wanted to."

---

### Stop 10 — Recommend, don't act; "likely," not "caused"  ·  *human-in-the-loop + causal humility*
**File:** `workflows/graph.py` → `n_human_review()` and `n_synthesize()`

**Common-sense version:** the system never changes a real system. Every recommendation is routed to an
**owner for human review** (`n_human_review()` raises a `HumanReviewRequest` with a risk level). And
because this is *observational* data, the system is honest about cause: it says a driver is a **"likely
driver"** or **"possible contributor,"** never "this caused it." That's real statistical humility —
correlation isn't causation, and the wording reflects it. The final answer is assembled
(`n_synthesize()`) tuned to what was actually asked, and always bundles: answer + evidence + definition
+ confidence + caveats + **owner action**.

> **Point at:** the `RECOMMENDATIONS` map + `grounded_action()` (plain-language next steps), and the
> "likely driver / possible contributor" labels. Tie it back to the read-only guardrail from Stop 3.

---

### Stop 11 — The flight recorder  ·  *observability / lineage / audit*
**File:** `skills/audit_skill.py`

**Common-sense version:** every decision and tool call is written to an append-only log
(`AuditLog.event()` / `.step()` / `.action()`), with safe summaries (no raw sensitive data). You can
replay exactly what happened, in order, with the rulebook version stamped on it. In a regulated
enterprise this *is* the difference between "trust me" and "here's the receipt."

> **Point at:** `event()` (machine audit) vs `step()` (the human-readable live trace you see running in
> the demo) vs `action()` (the recommendation log). Same engine, three audiences.

---

### Stop 12 — Proving it works  ·  *evaluation & reproducibility*
**Files:** `evals/validation.py`, `tests/`

**Common-sense version:** a capstone needs evidence it works, not just a nice screen. There are **two
layers**: (1) `validation.py` runs 15 automated checks — the seeded story is actually present, writes
are actually blocked, and every question routes to the right path; (2) `tests/` cover routing, SQL
safety, the human-review gate, and the investigation end-to-end. Because the data is built from a fixed
seed, **the same inputs always give the same evidence** — so anyone can reproduce and grade it.

> **Point at:** run `python -m evals.validation` (prints ALL CHECKS PASSED) and `python -m pytest`
> (25 passing). Reproducibility is itself a governance property.

---

### Stop 13 — One answer, four depths  ·  *progressive-disclosure UX*
**File:** `app/main.py`

**Common-sense version:** different people need different depth. The Streamlit app shows the *same*
answer at four levels: **Business answer** (for a leader) → **Evidence** (numbers + a chart matched to
the question) → **Trust details** (definitions, versions, the embedder) → **Technical audit** (the full
log). A shared formatter (`show_df` / `_col_fmt`) makes sure money shows as `$1,234` and rates as
`7.0%` everywhere — consistency is part of trustworthiness.

> **Point at:** the four tabs in the Live Demo, and `_col_fmt()` (the one place that decides how every
> number is formatted).

---

## How to give this as a live walkthrough (≈6–8 minutes)

Open files in **journey order** and say one sentence each. A reliable script:

1. `data/generator.py` — "Here's the fake-but-realistic store, with a *known* bad day seeded in."
2. `catalog/metrics.yaml` — "Here's the single rulebook of certified definitions — the source of truth."
3. `skills/sql_skill.py` → `check_sql` — "Before any query runs, this bouncer enforces read-only,
   approved-tables-only. Governance in code."
4. `skills/retrieval_skill.py` → `retrieve` — "RAG: it looks up the right definitions, and rejects any
   that are stale."
5. `skills/graph_skill.py` → `driver_path` — "A knowledge graph maps the metric to its drivers, tables,
   and the owning team."
6. `workflows/graph.py` → `build_workflow` + `classify_intent` — "This conductor runs the steps and
   decides whether one analyst or the whole team is needed."
7. `agents/team.py` → `dispatch` — "Seven specialists run in parallel; a failing one is isolated, not
   fatal."
8. `skills/tot_skill.py` → `score_branch` + `ungoverned_branch` — "Each explanation is scored 0–14;
   the ungoverned 'maybe prices rose' idea gets pruned automatically."
9. `skills/llm_skill.py` → `draft_answer` — "The language model only writes the sentence; it never
   invents a number."
10. `workflows/graph.py` → `n_human_review` — "Every recommendation goes to an owner; we say *likely*,
    not *caused*."
11. `evals/validation.py` — "And it's all proven by automated checks, reproducibly."

**The one line that summarizes the whole design:**
> *"Facts come from governed SQL over certified metrics; the AI only decides what to look at and how to
> phrase it — and every step is checked, labeled, and logged."*
