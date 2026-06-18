"""
Builds the 8-minute capstone deck in the requested flow:
pitch -> architecture & concepts -> demo -> live code walkthrough -> close.
Run: python presentation/build_deck_8min.py  ->  presentation/Omnichannel_8min.pptx
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
BLUE = RGBColor(0x25, 0x63, 0xEB)
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
    _para(tt.text_frame, title, 29, SLATE, bold=True, space_after=0, new=False)
    body = _box(s, Inches(0.7), Inches(1.9), Inches(11.9), Inches(4.9))
    tf = body.text_frame
    for text, level, bold in bullets:
        color = SLATE if level == 0 else GREY
        size = 18 if level == 0 else 15
        _para(tf, ("•  " if level == 0 else "–  ") + text, size, color, bold=bold,
              level=level, space_after=9 if level == 0 else 4)
    f = _box(s, Inches(0.6), Inches(7.0), Inches(11.6), Inches(0.4))
    _para(f.text_frame, "Omnichannel Retail Analytics Assistant  ·  CMU Capstone  ·  8-min", 10, GREY, new=False)
    pg = _box(s, Inches(12.5), Inches(7.0), Inches(0.6), Inches(0.4))
    _para(pg.text_frame, str(number), 11, GREY, bold=True, new=False)
    notes(s, note)
    return s


def section(number, kicker, title, lines, note):
    """Dark 'holder' slide for the live segments (demo / code walkthrough)."""
    s = prs.slides.add_slide(BLANK)
    _fill(s, 0, Inches(2.55), SW, Inches(0.10), CMU_RED)
    k = _box(s, Inches(0.9), Inches(1.7), Inches(11.5), Inches(0.5))
    _para(k.text_frame, kicker.upper(), 17, CMU_RED, bold=True, new=False)
    t = _box(s, Inches(0.9), Inches(2.75), Inches(11.5), Inches(1.0))
    _para(t.text_frame, title, 32, WHITE, bold=True, new=False)
    b = _box(s, Inches(0.9), Inches(3.95), Inches(11.5), Inches(2.6))
    tf = b.text_frame
    for ln in lines:
        _para(tf, ln, 16, LIGHT, space_after=8, new=(ln is not lines[0]))
    _fill_bg = None
    notes(s, note)
    # dark background behind everything
    s.shapes._spTree.remove(s.shapes[-1]._element)  # noop guard
    return s


def section_dark(number, kicker, title, lines, note):
    s = prs.slides.add_slide(BLANK)
    _fill(s, 0, 0, SW, SH, SLATE)
    _fill(s, 0, Inches(2.55), SW, Inches(0.10), CMU_RED)
    k = _box(s, Inches(0.9), Inches(1.6), Inches(11.5), Inches(0.5))
    _para(k.text_frame, kicker.upper(), 17, RGBColor(0xF8,0x71,0x71), bold=True, new=False)
    t = _box(s, Inches(0.9), Inches(2.65), Inches(11.5), Inches(1.0))
    _para(t.text_frame, title, 32, WHITE, bold=True, new=False)
    b = _box(s, Inches(0.9), Inches(3.9), Inches(11.5), Inches(2.8))
    tf = b.text_frame
    for i, ln in enumerate(lines):
        _para(tf, ln, 16, LIGHT, space_after=8, new=(i != 0))
    pg = _box(s, Inches(12.5), Inches(7.0), Inches(0.6), Inches(0.4))
    _para(pg.text_frame, str(number), 11, RGBColor(0x94,0xA3,0xB8), bold=True, new=False)
    notes(s, note)
    return s


# ===== 1 — Title + pitch + agenda =====
s = prs.slides.add_slide(BLANK)
_fill(s, 0, 0, SW, SH, SLATE)
_fill(s, 0, Inches(2.35), SW, Inches(0.10), CMU_RED)
t = _box(s, Inches(0.9), Inches(1.15), Inches(11.5), Inches(1.1))
_para(t.text_frame, "Omnichannel Retail Analytics Assistant", 40, WHITE, bold=True, new=False)
p = _box(s, Inches(0.9), Inches(2.6), Inches(11.5), Inches(1.5))
_para(p.text_frame, "A governed AI analyst that tells retail leaders why a KPI moved —",
      21, LIGHT, space_after=2, new=False)
_para(p.text_frame, "across every team, in seconds, using only certified data. It never guesses.",
      21, LIGHT)
ag = _box(s, Inches(0.9), Inches(4.5), Inches(11.5), Inches(1.5))
_para(ag.text_frame, "Today (8 min):  1) the pitch   2) architecture & concepts   "
                     "3) live demo   4) a quick code walkthrough", 16, WHITE, bold=True, new=False)
m = _box(s, Inches(0.9), Inches(6.5), Inches(11.5), Inches(0.6))
_para(m.text_frame, "Final Capstone  ·  Carnegie Mellon University  ·  Sreddy  ·  June 2026",
      13, RGBColor(0x94,0xA3,0xB8), new=False)
notes(s, "0:00–0:35. Say the 9-second pitch verbatim, then read the 4-part agenda in one line so they "
        "know the shape: pitch, architecture + concepts, demo, code walkthrough. Move fast.")

# ===== 2 — Architecture & concepts =====
content(
    2, "Part 2 · Architecture & the concepts I used",
    "Governed knowledge + a multi-agent reasoning loop",
    [("Source of truth — a versioned, hashed YAML catalog of certified metrics, approved tables, "
      "drivers, and guardrails.   [data governance / semantic layer]", 0, False),
     ("The loop (LangGraph state machine):   classify → retrieve → validate → relate → baseline → "
      "dispatch team → critic + beam → human review → answer.   [agent orchestration / ReAct]", 0, False),
     ("retrieve = RAG over a ChromaDB vector index;  relate = a NetworkX knowledge graph "
      "(metric → driver → table → owner).   [RAG + embeddings · knowledge graph]", 0, False),
     ("dispatch = 7 specialized analysts run in parallel;  the Critic scores each on a 0–14 rubric "
      "and beam search keeps the strongest.   [multi-agent systems · Tree-of-Thoughts + beam]", 0, False),
     ("The LLM only DRAFTS the prose — every number comes from governed SQL.   [LLM grounding]", 0, True),
     ("Read-only · causality labeled (not asserted) · human-in-the-loop · full audit trail.   "
      "[responsible AI / governance]", 0, False)],
    "0:35–2:35 (~2 min). This is the 'architecture + concepts' segment. Walk the loop left-to-right "
    "ONCE, then point at the bracketed concept tags — that's you naming the program vocabulary out "
    "loud: governance/semantic layer, RAG, knowledge graph, multi-agent, Tree-of-Thoughts/beam, LLM "
    "grounding, responsible AI. The ONE principle to land: facts come from governed SQL over certified "
    "metrics; the LLM only phrases them. You'll prove each of these in the code walkthrough next.")

# ===== 3 — DEMO =====
section_dark(
    3, "Part 3 · Live demo (~2.5 min)", "Seeing it run on a seeded 'bad day'",
    ["1.  'Why did conversion drop yesterday?' → team dispatch + live trace → drivers & evidence "
     "chart → owner actions + the human-review banner.",
     "2.  'Update the paid-social budget' → the read-only guardrail refuses.",
     "3.  An executive briefing → the multi-agent path ranks the biggest cross-functional issues."],
    "2:35–5:00 (~2.5 min). App already running and WARMED UP. (1) Run the conversion investigation; "
    "narrate the governed steps as the trace streams; land on Business answer → Evidence chart → owner "
    "actions + 🔴 human-review banner. (2) Type a write request → it refuses (fast, always lands). "
    "(3) Run one briefing. If time is tight, do #1 and #2 only. Keep a backup screenshot.")

# ===== 4 — Code walkthrough map =====
content(
    4, "Part 4 · Quick code walkthrough", "Six files — each is one concept, end to end",
    [("catalog/metrics.yaml — the certified definitions everything resolves to.   [governance / source of truth]", 0, False),
     ("skills/sql_skill.py · check_sql() — only read-only SELECTs over approved tables run.   [guardrails]", 0, False),
     ("skills/retrieval_skill.py · retrieve() — top-k vector lookup + a staleness/sync gate.   [RAG]", 0, False),
     ("workflows/graph.py · build_workflow() + classify_intent() — the LangGraph loop & routing.   [orchestration]", 0, False),
     ("agents/team.py · dispatch() — 7 analysts in parallel; a failure is isolated.   [multi-agent]", 0, False),
     ("skills/tot_skill.py · score_branch() + ungoverned_branch() — the 0–14 rubric prunes the "
      "ungoverned 'maybe prices rose' idea automatically.   [ToT/beam + responsible AI]", 0, False)],
    "5:00–7:30 (~2.5 min). Switch to your editor (VS Code). Open these SIX files in THIS order and say "
    "ONE sentence each (see the 'Code walkthrough — fast script' in CAPSTONE_SUBMISSION.md). Goal: show "
    "you understand the concepts, not read code line-by-line. The closer: in tot_skill.py point at "
    "ungoverned_branch() being pruned automatically — 'governance isn't a prompt, it's enforced.' "
    "If short on time, do metrics.yaml → sql_skill → graph.py → tot_skill (the 4 that best show "
    "understanding). Keep the files pre-opened as tabs so you don't fumble.")

# ===== 5 — Close =====
content(
    5, "Close", "From a 2-day fire drill to a governed answer in seconds",
    [("Fast AND trustworthy — the tension I opened with, resolved.", 0, False),
     ("The lesson: the hard part of agentic AI isn't generating answers — it's governing, "
      "evaluating, and observing them.", 0, True),
     ("Proven & reproducible: seeded ground truth, 15 validation checks, 25 tests, 0 UI exceptions — "
      "and 100% free/local.", 0, False),
     ("Extends to production: swap synthetic data for real tables behind the same catalog. "
      "Thank you — questions?", 0, False)],
    "7:30–8:00. Tie back to the opening promise (fast AND trustworthy) and deliver the one-sentence "
    "lesson. Drop the evaluation numbers as proof in one breath. One line on the production path, then "
    "thank them and open Q&A.")

import os
out = os.path.join(os.path.dirname(__file__), "Omnichannel_8min.pptx")
prs.save(out)
print("Saved:", out, "| slides:", len(prs.slides._sldIdLst))
