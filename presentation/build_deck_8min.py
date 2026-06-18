"""
Builds the CONDENSED 8-minute capstone deck (7 slides) for the Omnichannel Retail
Analytics Assistant. Run: python presentation/build_deck_8min.py
Produces presentation/Omnichannel_8min.pptx
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

CMU_RED = RGBColor(0xC4, 0x12, 0x30)
SLATE = RGBColor(0x1E, 0x29, 0x3B)
GREY = RGBColor(0x47, 0x55, 0x69)
LIGHT = RGBColor(0xF1, 0xF5, 0xF9)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Segoe UI"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
SW, SH = prs.slide_width, prs.slide_height


def _box(s, l, t, w, h):
    tb = s.shapes.add_textbox(l, t, w, h)
    tb.text_frame.word_wrap = True
    return tb


def _fill(s, l, t, w, h, color):
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    sh.fill.solid(); sh.fill.fore_color.rgb = color
    sh.line.fill.background(); sh.shadow.inherit = False
    return sh


def _para(tf, text, size, color, bold=False, level=0, space_after=8, italic=False, new=True):
    p = tf.add_paragraph() if (new and tf.paragraphs[0].runs) else tf.paragraphs[0]
    p.text = text; p.level = level; p.space_after = Pt(space_after)
    for r in p.runs:
        r.font.size = Pt(size); r.font.bold = bold; r.font.italic = italic
        r.font.color.rgb = color; r.font.name = FONT
    return p


def notes(s, text):
    s.notes_slide.notes_text_frame.text = text


def content(number, kicker, title, bullets, note, accent=CMU_RED):
    s = prs.slides.add_slide(BLANK)
    _fill(s, 0, 0, SW, Inches(0.18), accent)
    k = _box(s, Inches(0.6), Inches(0.42), Inches(12.1), Inches(0.4))
    _para(k.text_frame, kicker.upper(), 13, accent, bold=True, space_after=2, new=False)
    tt = _box(s, Inches(0.6), Inches(0.82), Inches(12.1), Inches(1.0))
    _para(tt.text_frame, title, 30, SLATE, bold=True, space_after=0, new=False)
    body = _box(s, Inches(0.7), Inches(1.95), Inches(11.9), Inches(4.9))
    tf = body.text_frame
    for text, level, bold in bullets:
        color = SLATE if level == 0 else GREY
        size = 19 if level == 0 else 16
        _para(tf, ("•  " if level == 0 else "–  ") + text, size, color, bold=bold,
              level=level, space_after=10 if level == 0 else 5)
    f = _box(s, Inches(0.6), Inches(7.0), Inches(11.6), Inches(0.4))
    _para(f.text_frame, "Omnichannel Retail Analytics Assistant  ·  CMU Capstone  ·  8-min", 10, GREY, new=False)
    pg = _box(s, Inches(12.5), Inches(7.0), Inches(0.6), Inches(0.4))
    _para(pg.text_frame, str(number), 11, GREY, bold=True, new=False)
    notes(s, note)
    return s


# ===== 1 — Title + 9-second pitch =====
s = prs.slides.add_slide(BLANK)
_fill(s, 0, 0, SW, SH, SLATE)
_fill(s, 0, Inches(2.5), SW, Inches(0.10), CMU_RED)
t = _box(s, Inches(0.9), Inches(1.25), Inches(11.5), Inches(1.2))
_para(t.text_frame, "Omnichannel Retail Analytics Assistant", 42, WHITE, bold=True, new=False)
p = _box(s, Inches(0.9), Inches(2.75), Inches(11.5), Inches(1.6))
_para(p.text_frame, "A governed AI analyst that tells retail leaders why a KPI moved —",
      22, LIGHT, space_after=2, new=False)
_para(p.text_frame, "across every team, in seconds, using only certified data. It never guesses.",
      22, LIGHT)
m = _box(s, Inches(0.9), Inches(5.7), Inches(11.5), Inches(1.2))
_para(m.text_frame, "Final Capstone  ·  Carnegie Mellon University  ·  Sreddy  ·  June 2026",
      15, WHITE, bold=True, new=False)
notes(s, "0:00–0:25. Lead with the 9-second pitch verbatim, then: 'In the next 8 minutes I'll show "
        "the problem, how it works, and a live demo.' Keep energy high; the demo is the star.")

# ===== 2 — Problem + solution =====
content(
    2, "Problem → solution", "Fast answers and trustworthy answers — usually you pick one",
    [("When a KPI moves, the 'why' spans many teams — marketing, merchandising, fulfillment, "
      "service, finance. Today that's a multi-day, multi-team fire drill.", 0, False),
     ("Generic 'chat-with-your-data' AI is fast but ungoverned: it invents metric definitions, "
      "runs arbitrary queries, and asserts causation. A confident wrong answer is a liability.", 0, False),
     ("My solution: a governed multi-agent analyst. Ask in plain English → it retrieves CERTIFIED "
      "definitions, runs read-only queries, reasons across domains, and returns:", 0, True),
     ("answer + evidence + the definition used + confidence + caveats + an owner-routed action.", 1, False),
     ("100% free and local — synthetic data, local models, nothing leaves the laptop.", 0, False)],
    "0:25–2:15. Frame the tension: fast AND trustworthy. Hit the two pains (speed + ungoverned AI) "
    "and land 'a confident wrong answer is a liability.' Then the one-line solution and the key idea: "
    "the answer is never just a number — it's a governed package with an owner action.")

# ===== 3 — How it works =====
content(
    3, "How it works", "Governed knowledge + a multi-agent reasoning loop",
    [("Source of truth: a versioned YAML catalog of certified metrics, approved tables, drivers, "
      "and guardrails — queried read-only over 18 tables in DuckDB.", 0, False),
     ("A LangGraph workflow runs the loop: classify → retrieve (RAG/ChromaDB) → validate (YAML) → "
      "relate (NetworkX graph) → dispatch a 7-analyst team in parallel → Critic scores each on a "
      "0–14 rubric → beam search keeps the strongest → human review → answer.", 0, False),
     ("The LLM is on a short leash — it only DRAFTS the prose; every number comes from governed SQL. "
      "No model running? A deterministic fallback writes it, so the demo can't break.", 0, True)],
    "2:15–3:45. One architecture slide. Read the loop quickly, then stress the design principle: the "
    "LLM never invents facts — it only phrases proven ones. Name the concepts as you go (RAG, knowledge "
    "graph, multi-agent, beam search) so the committee hears the program vocabulary. Mention the "
    "free/local fallback so they know the demo is robust.")

# ===== 4 — Trust / responsible AI =====
content(
    4, "Why it's trustworthy", "Governance enforced in code — the differentiator",
    [("Read-only guardrail: a SQL validator allows only SELECT over APPROVED tables; any write is "
      "blocked before it runs. (I'll show it refuse a write.)", 0, False),
     ("Certified definitions only — metrics resolve from the versioned, hashed catalog, never invented.", 0, False),
     ("Causality is LABELED, not asserted — 'likely driver' / 'possible contributor', never 'caused'.", 0, True),
     ("Human-in-the-loop — every recommendation routes to an owner; no system is changed automatically.", 0, False),
     ("Full audit trail + version/hash on every answer — reproducible and inspectable.", 0, False)],
    "3:45–4:45. This is what makes it a capstone, not a toy. Each line is an ENFORCED control, not a "
    "prompt. Emphasize causal humility (observational data → label likelihood) and human-in-the-loop + "
    "read-only = safe to deploy in a governed enterprise. Tease the guardrail demo.")

# ===== 5 — DEMO =====
s = prs.slides.add_slide(BLANK)
_fill(s, 0, 0, SW, SH, SLATE)
_fill(s, 0, Inches(2.7), SW, Inches(0.10), CMU_RED)
k = _box(s, Inches(0.9), Inches(2.0), Inches(11.5), Inches(0.5))
_para(k.text_frame, "LIVE DEMO  ·  ~3 minutes", 18, CMU_RED, bold=True, new=False)
t = _box(s, Inches(0.9), Inches(2.9), Inches(11.5), Inches(1.0))
_para(t.text_frame, "On a seeded 'bad day'", 34, WHITE, bold=True, new=False)
b = _box(s, Inches(0.9), Inches(4.1), Inches(11.5), Inches(2.2))
tf = b.text_frame
_para(tf, "1.  'Why did conversion drop yesterday?' — team dispatch, live trace, drivers + "
          "evidence chart, owner actions, human-review banner.", 17, LIGHT, space_after=9, new=False)
_para(tf, "2.  'Update the paid-social budget' — the read-only guardrail refuses.", 17, LIGHT, space_after=9)
_para(tf, "3.  An executive briefing — the multi-agent path ranks the biggest cross-functional issues.", 17, LIGHT)
notes(s, "4:45–7:45 (your centerpiece — keep it tight). App already running & warmed up. (1) Run the "
        "conversion investigation; narrate the governed steps while the trace streams; land on Business "
        "answer → Evidence chart → owner actions + human-review banner. (2) Show the write refusal — "
        "fast, always lands. (3) Run ONE briefing to show cross-functional ranking. Have a backup "
        "screenshot. If short on time, do #1 and #2 only.")

# ===== 6 — Evaluation & feasibility =====
content(
    6, "Does it work?", "Reproducible, validated, and free to run",
    [("Seeded ground truth: a fixed-seed world with a known story (conversion down ~23% from a "
      "paid-social shift, stockouts, and regional delays) — so I can verify it finds the right drivers.", 0, False),
     ("Automated checks: 15 data/guardrail/routing validations pass; 25 tests pass; the UI renders "
      "all pages with 0 exceptions.", 0, False),
     ("Reproducible by design — same seed, same evidence — and 100% free/local, no paid APIs.", 0, True)],
    "7:45–8:15 (overrun budget). Two evaluation layers: known ground truth + automated gates "
    "(data, guardrails, routing). Reproducibility from a fixed seed is itself a governance property. "
    "Keep this to ~20 seconds if the demo ran long.")

# ===== 7 — Impact / close =====
content(
    7, "Why it matters", "From a 2-day fire drill to a governed answer in seconds",
    [("Impact: fast AND trustworthy — the tension we started with, resolved.", 0, False),
     ("The lesson: the hard part of agentic AI isn't generating answers — it's governing, "
      "evaluating, and observing them.", 0, True),
     ("Extends to production: swap synthetic data for real warehouse tables behind the same catalog; "
      "the governance and reasoning are unchanged.", 0, False),
     ("Thank you — happy to take questions.", 0, False)],
    "8:15–8:30. Close on the opening promise (fast AND trustworthy) and the one-sentence lesson. "
    "Give the production path in one line to show it scales. Thank them and open Q&A.")

import os
out = os.path.join(os.path.dirname(__file__), "Omnichannel_8min.pptx")
prs.save(out)
print("Saved:", out, "| slides:", len(prs.slides._sldIdLst))
