# Demo Script — click-by-click (≈7 minutes)

**Before you start (off-camera):**
- Launch the app: `python tools.py run` → open `http://localhost:8501`.
- Pre-load it once so the first-run data build / index is warm (the first investigation is the slow one).
- Open the app at **🔬 Live Demo**. Zoom the browser to ~110–125% so text is readable on the recording.
- Have one **backup screenshot/GIF** of a completed investigation in case the laptop stalls mid-record.

> Narrate **intent first, mechanics second**: say what a user wants, then let the system earn the answer.

---

## Part 1 — Flagship investigation (≈4 min) ★ the money shot

1. **Set up the question.** "A leader sees conversion fell yesterday and asks the obvious question."
   Pick: **"Why did digital conversion drop yesterday compared with the prior 7-day average?"**
   Click **Run investigation**.
2. **While the live trace streams**, narrate the governed steps (don't read them — point):
   - "It classifies the question, retrieves the **certified** conversion definition, validates it,
     and maps the metric to candidate drivers through the graph."
   - "It confirms the drop against the prior-7-day baseline — about **−23%** — then dispatches **seven
     specialized analysts in parallel**, one read-only query each."
   - "A Critic scores every hypothesis on a 0–14 rubric; beam search keeps the strongest drivers and
     **prunes the ungoverned one** — note it blocked a query against a non-approved table."
3. **Business answer tab.** "Here's the leader's answer: conversion down ~23%, with the **likely
   drivers** — paid-social shift, stockouts, regional delivery delays — each labeled by confidence and
   **routed to an owner**." Point at the **🔴 Human-review banner**: "Nothing is changed automatically;
   it's routed for owner review."
4. **Evidence tab.** "Same answer, one level deeper for an analyst — the actual numbers and a chart
   **matched to the question**, plus the validated, read-only SQL."
5. **Trust details tab (briefly).** "And for governance: the certified definition, the **catalog
   version and content hash**, the embedder, and a full step-by-step audit log. Every claim is traceable."

> If it's slow, this is a feature: "while the team runs, notice the trace is fully transparent —
> nothing here is a black box."

---

## Part 2 — The read-only guardrail (≈1 min) ★ always gets a reaction

6. In the question box type: **"update the paid-social budget to 50%"** → Run.
7. "It **refuses** — the SQL validator only allows read-only SELECTs over approved tables. The system
   *cannot* write to an operational system, by construction. That's governance enforced in code, not a
   promise in a prompt."

---

## Part 3 — Executive briefing (≈2 min) ★ shows the multi-agent path beyond conversion

8. From the dropdown, **Executive briefings** group → "Across all teams, what are the top
   cross-functional risks we should act on now?"
9. "Same multi-agent engine, different job: it ranks the **biggest issues across every domain** by
   evidence strength — here the top priority is **inventory/merchandising**, not conversion — and gives
   each owner a concrete, **data-grounded action**." Point at one **Act now** item and its basis numbers.
10. Close the demo: "Answer, evidence, governance, and an owner action — in seconds, fully auditable."

---

## Recovery lines (if something misbehaves)
- App stalls: "Let me show the completed run I captured earlier" → switch to backup screenshot, keep talking.
- Wrong tab: "Four trust levels here — let me jump to the one that matters."
- Model/LLM warning: "That's the optional local LLM; the system falls back to deterministic prose, so the
  numbers are identical either way."
