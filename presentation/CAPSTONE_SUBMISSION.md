# Capstone submission — the crisp version

Three deliverables: **(1) a clean repo, (2) a 9-second pitch, (3) an 8-minute video.**
Everything you need is below; the 8-minute deck is `presentation/Omnichannel_8min.pptx`.

---

## 1) Clean git repo — share checklist

The repo is already tidy. Before you share, confirm:

- [ ] **`main` is current** — all work merged; `git status` clean; no stray files.
- [ ] **README is the front door** — it opens with what/why, a one-command quick start
      (`python tools.py`), the 5 app pages, the free/local stack, and the repo layout. (Updated.)
- [ ] **It runs from a clean clone** — `python tools.py` → app at `http://localhost:8501`.
- [ ] **Tests/validation pass** — `python -m evals.validation` (ALL CHECKS PASSED) and `python -m pytest` (25 passed).
- [ ] **No secrets** — only `.env.example` is committed; there are no API keys (the stack is free/local).
- [ ] **Presentation materials included** — `presentation/` has the deck, scripts, and code walkthrough.

**What to send:** the GitHub repo link (or a zip of a fresh clone). One line for the reviewer:
> "Clone and run `python tools.py` — it sets up, validates, and launches the app. Everything is free
> and local; no keys needed."

---

## 2) The 9-second pitch (≈24 words — say it in one breath)

**Use this one:**
> *"A governed AI analyst that tells retail leaders why a KPI moved — across every team, in seconds,
> using only certified data. It never guesses."*

**Alternates:**
- *"When a retail KPI drops, finding out why takes days across five teams. My governed AI analyst does
  it in seconds — and it never invents the answer."*
- *"It's an AI analyst for retail that investigates why your metrics moved across every team — grounded
  only in governed data, labeling likelihood instead of guessing at cause."*

> Delivery: land hard on the contrast — **"in seconds … never guesses."** That's the whole project.

---

## 3) The 8-minute video — run sheet

**Flow you asked for:** pitch → architecture & concepts → demo → code walkthrough → close.
Deck: `Omnichannel_8min.pptx` (5 slides, notes on each).

| Time | Slide | Segment | Say (one beat) |
|---|---|---|---|
| 0:00–0:35 | 1 Title | **Pitch + agenda** | Say the **9-second pitch** verbatim, then the 4-part agenda in one line. |
| 0:35–2:35 | 2 Architecture | **Architecture & concepts** | Walk the loop once, then point at the bracketed **concept tags** (governance/semantic layer, RAG, knowledge graph, multi-agent, ToT/beam, LLM grounding, responsible AI). Land: *facts come from governed SQL; the LLM only phrases them.* |
| 2:35–5:00 | 3 Demo | **Live demo (app)** | (1) "Why did conversion drop?" — trace, drivers + chart, owner actions, review banner. (2) "Update the budget" → **refused**. (3) one **executive briefing**. |
| 5:00–7:30 | 4 Code walkthrough | **Code (editor)** | Open 6 files, one sentence each (script below). Close on `ungoverned_branch()` being pruned automatically. |
| 7:30–8:00 | 5 Close | **Close** | "Fast and trustworthy." Lesson + evaluation numbers as proof. Thank you. |

**The three things that must land** (graders reward these):
1. **A real business problem** — fast *and* trustworthy, not a tech demo.
2. **Governance enforced in code** — read-only validator, certified definitions, audit trail. The differentiator vs. "chat with your data."
3. **You understand the concepts** — the architecture slide *names* them, the code walkthrough *shows* them.

**If you run long:** in the demo do only #1 and #2; in the code walkthrough do only the four starred files
below. **Never** let the demo drop below ~2 minutes — it's the proof.

---

## Code walkthrough — fast script (~2.5 min, in your editor)

Pre-open these as tabs in VS Code so you don't fumble. Open in order; one sentence each. ★ = keep if short on time.

1. ★ **`catalog/metrics.yaml`** — "Everything resolves to this one rulebook of *certified* metric
   definitions — the single source of truth. No definitions are invented anywhere else." *[governance / semantic layer]*
2. ★ **`skills/sql_skill.py` → `check_sql()`** — "Before any query runs, this bouncer allows only
   read-only SELECTs over approved tables — a write is blocked *before* it executes." *[guardrails / responsible AI]*
3. **`skills/retrieval_skill.py` → `retrieve()`** — "This is the RAG step: a top-k vector lookup over the
   catalog, and it rejects any chunk whose fingerprint is stale." *[RAG + embeddings]*
4. ★ **`workflows/graph.py` → `build_workflow()` + `classify_intent()`** — "The LangGraph state machine: it
   classifies the question, then runs the governed loop — and decides whether one analyst or the whole
   team is needed." *(also point at `n_human_review` — every recommendation routes to an owner)* *[orchestration / human-in-the-loop]*
5. **`agents/team.py` → `dispatch()`** — "Seven specialist analysts run in parallel, each with its own
   query and timeout; a failing one is isolated, not fatal." *[multi-agent systems]*
6. ★ **`skills/tot_skill.py` → `score_branch()` + `ungoverned_branch()`** — "Each explanation is scored on a
   0–14 rubric; and this planted *ungoverned* 'maybe prices rose' hypothesis gets **pruned automatically**
   because it has no certified metric. Governance isn't a prompt — it's enforced." *[Tree-of-Thoughts/beam + responsible AI]*

**The closing line for this segment:**
> "So the AI decides *what to look at* and *how to phrase it* — but every fact is governed, checked, and
> logged." *(Full version: `presentation/CODE_WALKTHROUGH.md`.)*

---

## Demo — fast script (≈3 min)

> App already running and **warmed up** (run one investigation before recording so the first slow build isn't on camera). Browser zoom ~110–125%.

1. **Conversion investigation (~1:45).** Ask *"Why did digital conversion drop yesterday compared with
   the prior 7-day average?"* → **Run**. While the trace streams: "it retrieves the *certified*
   definition, checks a baseline — about **−23%** — then dispatches **seven analysts in parallel**, and
   a Critic prunes the ungoverned hypothesis." Land on **Business answer** (drivers + confidence +
   owners), then **Evidence** (chart matched to the question), then point at the **🔴 human-review
   banner** — "nothing changes automatically."
2. **Guardrail (~0:30).** Type *"update the paid-social budget to 50%"* → **Run** → "it **refuses** —
   read-only by construction. Governance in code, not a prompt." (Reliable crowd-pleaser.)
3. **Executive briefing (~0:45).** Pick a briefing question → "same multi-agent engine, different job:
   it ranks the **biggest issues across every domain** and gives each owner a data-grounded action."

**Recovery line:** if anything stalls — "while it runs, notice the trace is fully transparent — nothing
here is a black box" — or cut to your backup screenshot.

---

## Recording (Windows, quickest reliable path)

Zoom → **New Meeting** → **Share Screen → full desktop** → **Record on this Computer** → present slides +
demo in one take → **End Meeting** gives an `.mp4`. Use a **headset mic**, silence notifications
(Win+N), and do a 60-second test first. (Full options in `RECORDING_GUIDE.md`; OBS Studio if you want
1080p with a webcam overlay.)
