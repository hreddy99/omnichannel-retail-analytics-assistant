"""
Generate a standalone, interactive HTML version of the project plan.

Self-contained (inline CSS + vanilla JS): collapsible sections, a sticky table
of contents, and styled tables. Importable by the Streamlit app (render_html)
or runnable from the CLI:

    python build_html.py        # writes project_plan.html
"""
from __future__ import annotations

import html
import pathlib

from src import plan_content as P

OUT = pathlib.Path(__file__).resolve().parent / "project_plan.html"


def _esc(x) -> str:
    return html.escape(str(x))


def _table(headers, rows) -> str:
    th = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    trs = []
    for r in rows:
        tds = "".join(f"<td>{_esc(c)}</td>" for c in r)
        trs.append(f"<tr>{tds}</tr>")
    return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table>"


def _section(num, sid, title, body) -> str:
    return f"""
    <section class="card" id="{sid}">
      <h2 onclick="toggle('{sid}')"><span class="num">{num}</span>{_esc(title)}
        <span class="chev">▾</span></h2>
      <div class="body">{body}</div>
    </section>"""


def render_html() -> str:
    secs = []

    secs.append(_section(1, "summary", "Executive Summary",
                         f"<p>{_esc(P.EXECUTIVE_SUMMARY)}</p>"))

    secs.append(_section(2, "feasibility", "Feasibility Decision",
                         f'<p class="callout ok">{_esc(P.FEASIBILITY)}</p>'
                         '<div class="badges"><span class="badge">0 paid services</span>'
                         '<span class="badge">0 external APIs to run demo</span>'
                         '<span class="badge">Runs offline</span></div>'))

    secs.append(_section(3, "problem", "Business Problem & Users",
                         f"<p>{_esc(P.BUSINESS_PROBLEM)}</p>"))

    secs.append(_section(4, "capstone", "Capstone Fit & Course Alignment",
                         _table(["Concept", "How it's demonstrated", "Success measure"],
                                P.CAPSTONE_FIT)))

    secs.append(_section(5, "stack", "Free & Local Tool Stack",
                         _table(["Tool", "Role", "Free / on PC?", "MVP notes"], P.TOOL_STACK)))

    secs.append(_section(6, "arch", "Updated Architecture",
                         _table(["Layer", "Responsibility"], P.ARCH_LAYERS)))

    rubric_rows = [(c, f"0–{m}") for c, m in P.TOT_RUBRIC]
    rubric_rows.append(("Maximum total", sum(m for _, m in P.TOT_RUBRIC)))
    secs.append(_section(7, "tot", "Tree-of-Thought Scoring Strategy",
                         "<p>Bounded beam search — width 2, depth 2 — activated only when "
                         "multiple plausible driver paths compete.</p>"
                         + _table(["Evaluation criterion", "Score"], rubric_rows)
                         + f'<p class="note">{_esc(P.TOT_THRESHOLDS)}</p>'))

    secs.append(_section(8, "conflict", "Source Conflict & Priority Rules",
                         _table(["Situation", "Decision rule", "User-facing behavior"],
                                P.CONFLICT_RULES)))

    secs.append(_section(9, "data", "Synthetic Data Plan",
                         _table(["Seeded scenario", "Injected pattern", "Expected evidence", "Owner"],
                                P.SCENARIOS)))

    q_items = "".join(f"<li>{_esc(q)}</li>" for q in P.DEMO_QUESTIONS)
    secs.append(_section(10, "questions", "MVP Demo Questions", f"<ol>{q_items}</ol>"))

    secs.append(_section(11, "fr", "Functional Requirements",
                         _table(["ID", "Requirement", "Acceptance criteria"], P.FUNC_REQS)))

    secs.append(_section(12, "milestones", "Implementation Milestones",
                         _table(["Phase", "Deliverables", "Exit criteria"], P.MILESTONES)))

    secs.append(_section(13, "risks", "Risks & Mitigations",
                         _table(["Risk", "Mitigation"], P.RISKS)))

    secs.append(_section(14, "status", "Prototype Status (this repository)",
                         _table(["Component", "Status", "Notes"], P.PROTOTYPE_STATUS)))

    toc = "".join(
        f'<a href="#{sid}" onclick="ensureOpen(\'{sid}\')">{num}. {_esc(title)}</a>'
        for num, sid, title in [
            (1, "summary", "Executive Summary"), (2, "feasibility", "Feasibility"),
            (3, "problem", "Business Problem"), (4, "capstone", "Capstone Fit"),
            (5, "stack", "Tool Stack"), (6, "arch", "Architecture"),
            (7, "tot", "ToT Strategy"), (8, "conflict", "Conflict Rules"),
            (9, "data", "Synthetic Data"), (10, "questions", "Demo Questions"),
            (11, "fr", "Functional Reqs"), (12, "milestones", "Milestones"),
            (13, "risks", "Risks"), (14, "status", "Prototype Status")])

    return _TEMPLATE.format(title=_esc(P.TITLE), subtitle=_esc(P.SUBTITLE),
                            toc=toc, sections="".join(secs))


_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --blue:#2563eb; --ink:#0f172a; --muted:#64748b; --line:#e2e8f0; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
         color:var(--ink); background:#f8fafc; line-height:1.55; }}
  header {{ background:linear-gradient(135deg,#1e3a8a,#2563eb); color:white;
           padding:34px 24px; }}
  header h1 {{ margin:0 0 4px; font-size:1.9rem; }}
  header p {{ margin:0; opacity:.9; }}
  .wrap {{ display:grid; grid-template-columns:240px 1fr; gap:24px; max-width:1180px;
          margin:24px auto; padding:0 18px; }}
  nav {{ position:sticky; top:18px; align-self:start; background:white; border:1px solid var(--line);
        border-radius:10px; padding:14px; max-height:90vh; overflow:auto; }}
  nav b {{ font-size:.8rem; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }}
  nav a {{ display:block; padding:6px 8px; color:var(--ink); text-decoration:none; border-radius:6px;
          font-size:.9rem; }}
  nav a:hover {{ background:#eff6ff; color:var(--blue); }}
  .card {{ background:white; border:1px solid var(--line); border-radius:10px; margin:0 0 16px;
          overflow:hidden; }}
  .card h2 {{ margin:0; padding:16px 18px; font-size:1.15rem; cursor:pointer; display:flex;
             align-items:center; gap:10px; user-select:none; }}
  .card h2:hover {{ background:#f1f5f9; }}
  .num {{ background:var(--blue); color:white; width:26px; height:26px; border-radius:50%;
         display:inline-grid; place-items:center; font-size:.8rem; flex:none; }}
  .chev {{ margin-left:auto; color:var(--muted); transition:transform .2s; }}
  .card.collapsed .chev {{ transform:rotate(-90deg); }}
  .body {{ padding:0 18px 18px; }}
  .card.collapsed .body {{ display:none; }}
  table {{ width:100%; border-collapse:collapse; margin:8px 0; font-size:.9rem; }}
  th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line);
          vertical-align:top; }}
  th {{ background:#f1f5f9; color:#334155; }}
  .callout {{ padding:12px 14px; border-radius:8px; }}
  .callout.ok {{ background:#dcfce7; border-left:4px solid #16a34a; }}
  .badges {{ margin-top:10px; }}
  .badge {{ display:inline-block; background:#eff6ff; color:var(--blue); border:1px solid #bfdbfe;
           padding:4px 10px; border-radius:999px; font-size:.8rem; margin:2px 6px 2px 0; }}
  .note {{ color:var(--muted); font-size:.88rem; }}
  footer {{ text-align:center; color:var(--muted); padding:24px; font-size:.85rem; }}
  .controls {{ max-width:1180px; margin:0 auto; padding:0 18px; }}
  .controls button {{ background:white; border:1px solid var(--line); border-radius:8px;
                     padding:8px 14px; cursor:pointer; margin-right:8px; }}
  @media(max-width:820px){{ .wrap{{grid-template-columns:1fr;}} nav{{position:static;}} }}
</style></head>
<body>
<header><h1>{title}</h1><p>{subtitle}</p></header>
<div class="controls" style="margin-top:16px;">
  <button onclick="setAll(false)">Expand all</button>
  <button onclick="setAll(true)">Collapse all</button>
</div>
<div class="wrap">
  <nav><b>Contents</b>{toc}</nav>
  <main>{sections}</main>
</div>
<footer>Generated from the project plan · read-only synthetic prototype · free &amp; local stack</footer>
<script>
  function toggle(id){{ document.getElementById(id).classList.toggle('collapsed'); }}
  function ensureOpen(id){{ document.getElementById(id).classList.remove('collapsed'); }}
  function setAll(collapsed){{
    document.querySelectorAll('.card').forEach(function(c){{
      c.classList.toggle('collapsed', collapsed);
    }});
  }}
</script>
</body></html>"""


if __name__ == "__main__":
    OUT.write_text(render_html(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")
