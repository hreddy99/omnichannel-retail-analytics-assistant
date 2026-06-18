# Talking Points — Omnichannel Retail Analytics Assistant
### CMU Capstone · 20-minute presentation

**Format:** ~11 min talk → ~7 min live demo → ~1 min close → Q&A.
Every slide also has these notes embedded in the .pptx (View → Notes).

**One-sentence thesis (memorize this):**
> "I built an AI analyst that answers cross-functional retail performance questions in
> seconds — but only from governed, certified data, and it labels likelihood instead of
> guessing at cause."

---

## Timing map

| Time | Slide | Beat |
|---|---|---|
| 0:00–0:45 | 1 Title | Hook + what they'll see |
| 0:45–2:30 | 2 Problem | Slow **and** untrustworthy |
| 2:30–3:45 | 3 Users | Roles → questions → one source of truth |
| 3:45–5:30 | 4 Solution | Answer + evidence + owner action; 3 modes; free/local |
| 5:30–7:30 | 5 Architecture | Data platform + governed knowledge + reasoning |
| 7:30–9:00 | 6 Trust | Governance enforced in code |
| 9:00–11:00 | 7 Multi-agent | Why a team, when not, the trade-offs |
| 11:00–18:00 | 8 **DEMO** | The centerpiece (see DEMO script below) |
| 18:00–19:00 | 9 Evaluation | Reproducible, validated, 0 exceptions |
| 19:00–19:40 | 10 Trade-offs | Decisions + honest limits |
| 19:40–20:00 | 11 Impact | Lesson + roadmap, then thank you |
| — | 12 Thank you | Q&A |

> If you're running long, the demo is protected — cut slide 10 to two sentences and
> merge 9+11. Never cut the demo below 5 minutes.

---

## Core elements to make sure land (what graders reward)

1. **A real, framed business problem** — fast *and* trustworthy, not a tech demo looking for a use.
2. **Governance enforced in code** — read-only SQL validator, certified-definitions-only, versioned/hashed catalog. This is the differentiator.
3. **Intellectual honesty** — causality is *labeled* (likely driver / possible contributor), never asserted; you name your own limitations.
4. **A justified multi-agent design** — parallel + specialized, with trade-offs you bounded, and a rule for *when not* to use it.
5. **A working, reproducible system** — live demo + automated evaluation from a fixed seed; 0 render exceptions.
6. **Engineering maturity** — feasibility (free/local), observability (audit trail), human-in-the-loop.

---

## Slide-by-slide cues

- **1 Title:** Open with the fire drill. "Conversion drops. The CEO asks *why*. Today that's a
  two-day, five-team investigation. Watch this." Name yourself; promise a live demo.
- **2 Problem:** Two pains — speed (siloed data) and trust (ungoverned AI hallucinates definitions,
  runs arbitrary SQL, claims causation). Land: *a confident wrong answer routed to the wrong team is
  worse than a slow one.*
- **3 Users:** These personas are in my catalog; each maps to an analyst agent **and** an owner. The
  trick: everyone asks in plain English, all resolve to the **same certified metric**.
- **4 Solution:** Answer is never just a number — it's answer + evidence + definition + confidence +
  caveat + owner action. Three modes (investigation / direct & themed / executive briefing). 100% free
  and local — the plan's MVP claim, proven end to end.
- **5 Architecture:** Top-to-bottom: medallion data → governed knowledge (YAML = source of truth,
  ChromaDB, NetworkX) → LangGraph reasoning → Streamlit with four trust levels. **The LLM drafts prose
  only; it never invents numbers or definitions.** Deterministic fallback if no model — demo can't break.
- **6 Trust:** Each control is *enforced*: the guardrail is a validator that refuses the query, not a
  polite request to the model. Causality labeled. Human-in-the-loop. Versioned + hashed + audited.
- **7 Multi-agent:** WHY — the problem is genuinely parallel and specialized. WHEN NOT — narrow
  questions use one analyst (the ToT gate decides). Critic scores each hypothesis on a 0–14 rubric;
  beam keeps the strongest. Trade-offs accepted (coordination, complexity, non-determinism) and bounded.
- **8 DEMO:** see below.
- **9 Evaluation:** Known ground truth (seeded) + automated checks (data, guardrails, routing) + full
  coverage with 0 exceptions + reproducible from a fixed seed = auditable.
- **10 Trade-offs:** Each decision deliberate with a rationale; then own the limits (observational data,
  single-day scenario, demo-scoped catalog).
- **11 Impact:** "The hard part of agentic AI isn't generating answers — it's governing, evaluating, and
  observing them." Roadmap: real warehouse tables behind the same catalog. Thank them.

---

## Q&A — rehearsed answers (20–30s each)

- **"How do you know the drivers are real?"** Seeded ground truth I can validate against, plus the
  Critic's evidence rubric. I report *likelihood*, not proof — that's deliberate.
- **"Why not just point GPT-4 at the warehouse?"** Governance. Certified definitions, a read-only
  validator, and an audit trail. An ungoverned LLM can't give consistent, safe, inspectable answers —
  which is the enterprise requirement.
- **"Is it production-ready?"** The *governance architecture* is. Swap synthetic data for real tables
  behind the same YAML catalog; the controls and reasoning are unchanged.
- **"Why multi-agent and not one big prompt?"** The work is parallel and specialized, and isolating a
  failing agent keeps the system robust. Single-domain questions deliberately use one analyst.
- **"What was hardest?"** Restraint — keeping the LLM away from facts, and building the evaluation and
  guardrails so the system is trustworthy by construction.
