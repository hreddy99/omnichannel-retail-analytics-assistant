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

**Shape:** ~4.5 min talk · ~3 min demo · ~0.5 min close. Deck: `Omnichannel_8min.pptx` (7 slides, notes on each).

| Time | Slide | Say (one beat) |
|---|---|---|
| 0:00–0:25 | 1 Title | Open with the **9-second pitch**, then "here's the problem, how it works, and a live demo." |
| 0:25–2:15 | 2 Problem→Solution | Fast **and** trustworthy. Pain: siloed (slow) + ungoverned AI (hallucinated definitions, asserted cause). Solution: answer = number **+ evidence + definition + confidence + caveat + owner action.** Free/local. |
| 2:15–3:45 | 3 How it works | YAML catalog = source of truth. LangGraph loop: classify → retrieve (RAG) → validate → graph → **7 analysts in parallel** → Critic 0–14 → beam → human review. **LLM drafts prose only; never invents numbers.** |
| 3:45–4:45 | 4 Trustworthy | Each control is **enforced in code**: read-only validator, certified-definitions-only, **causality labeled not asserted**, human-in-the-loop, full audit + version hash. |
| 4:45–7:45 | 5 **DEMO** | (1) "Why did conversion drop?" — trace, drivers + chart, owner actions, review banner. (2) "Update the budget" → **refused**. (3) one **executive briefing**. |
| 7:45–8:15 | 6 Evaluation | Seeded ground truth + 15 checks + 25 tests + 0 render exceptions; reproducible & free. |
| 8:15–8:30 | 7 Close | "Fast and trustworthy." Lesson: *the hard part of agentic AI is governing, evaluating, observing — not generating.* Thank you. |

**The three things that must land** (graders reward these):
1. **A real business problem** — fast *and* trustworthy, not a tech demo.
2. **Governance enforced in code** — read-only validator, certified definitions, audit trail. The differentiator vs. "chat with your data."
3. **Intellectual honesty** — causality *labeled*, not claimed; recommend, don't act.

**If you run long:** cut slide 6 to one sentence and merge it into slide 7; in the demo, do only #1 and #2.
**Never** let the demo drop below ~2 minutes — it's the proof.

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
