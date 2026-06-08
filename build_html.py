"""
Generate a standalone, interactive HTML version of the detailed project plan.

Self-contained (inline CSS + vanilla JS): collapsible sections, a sticky table
of contents, expand/collapse all, and styled tables. Importable by the Streamlit
app (render_html) or runnable from the CLI:

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
    trs = "".join("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"


def _section(num, sid, title, body) -> str:
    return (f'<section class="card" id="{sid}"><h2 onclick="toggle(\'{sid}\')">'
            f'<span class="num">{num}</span>{_esc(title)}<span class="chev">▾</span></h2>'
            f'<div class="body">{body}</div></section>')


SECTIONS = [
    ("summary", "Executive Summary", lambda: f"<p>{_esc(P.EXECUTIVE_SUMMARY)}</p>"),
    ("feasibility", "Feasibility Decision",
     lambda: f'<p class="callout ok">{_esc(P.FEASIBILITY)}</p><div class="badges">'
             '<span class="badge">0 paid services</span><span class="badge">read-only</span>'
             '<span class="badge">runs on a personal PC</span></div>'),
    ("problem", "Business Problem & Users",
     lambda: f"<p>{_esc(P.BUSINESS_PROBLEM)}</p>"
             + _table(["Role", "Typical question", "Assistant value"], P.BUSINESS_ROLES)),
    ("enterprise", "Enterprise Analytics & Modern Data Platform",
     lambda: f"<p>{_esc(P.ENTERPRISE_ALIGNMENT)}</p>"
             + _table(["Medallion layer", "Role"], P.MEDALLION)
             + f'<p class="note">{_esc(P.MEDALLION_NOTE)}</p>'
             + _table(["Source / OLTP system", "Enterprise analytics role", "Assistant use"], P.OLTP_RELATIONSHIP)
             + "<ul>" + "".join(f"<li>{_esc(v)}</li>" for v in P.ENTERPRISE_VALUE) + "</ul>"),
    ("capabilities", "Agentic Capability Alignment",
     lambda: _table(["Capability", "How the assistant implements it", "What good looks like"], P.CAPABILITY_ALIGNMENT)),
    ("roadmap", "Phase Roadmap",
     lambda: _table(["Phase", "Objective", "Scope", "Success criteria"], P.PHASE_ROADMAP)),
    ("stack", "Free & Local Tool Stack",
     lambda: _table(["Tool", "Role", "Free / on PC?", "MVP notes"], P.TOOL_STACK)),
    ("arch", "Architecture",
     lambda: _table(["Layer", "Component", "Responsibility", "Control"], P.ARCH_LAYERS)),
    ("yaml", "Knowledge Layer — YAML Catalog Files",
     lambda: _table(["File", "Contents", "Used by"], P.YAML_FILES)),
    ("graph", "NetworkX Knowledge Graph",
     lambda: _table(["Object", "Examples", "Purpose"], P.GRAPH_OBJECTS)),
    ("agents", "Agent Design & Reasoning Loop",
     lambda: _table(["Agent / role", "Purpose", "Primary tools", "MVP output"], P.AGENT_ROLES)),
    ("team", "Multi-Agent Team — Specialization, Parallelism & Trade-offs",
     lambda: f"<p>{_esc(P.MULTI_AGENT_INTRO)}</p>"
             + _table(["Analyst", "Domain", "Phase", "Governed driver / focus"], P.ANALYST_TEAM)
             + _table(["Phase", "Analysts added", "Focus"], P.PHASE_TEAM)
             + "<p class='note'><b>When we use multiple agents</b></p>"
             + _table(["Decision", "Rationale"], P.MULTI_AGENT_WHEN)
             + "<p class='note'><b>Trade-offs accepted &amp; mitigations</b></p>"
             + _table(["Trade-off", "Mitigation"], P.MULTI_AGENT_TRADEOFFS)),
    ("tot", "Conditional Tree-of-Thought Beam Search",
     lambda: _table(["ToT element", "Definition"], P.TOT_DEPTH)
             + _table(["Evaluation criterion", "Score"],
                      [(c, f"0–{m}") for c, m in P.TOT_RUBRIC]
                      + [("Maximum total", sum(m for _, m in P.TOT_RUBRIC))])
             + f'<p class="note">{_esc(P.TOT_THRESHOLDS)}</p>'),
    ("conflict", "Source Conflict & Priority Rules",
     lambda: _table(["Situation", "Decision rule", "User-facing behavior"], P.CONFLICT_RULES)),
    ("data", "Synthetic Data Plan",
     lambda: _table(["Table", "Grain", "Phase I role"], P.SYNTH_TABLES)
             + _table(["Seeded scenario", "Pattern", "Expected evidence", "Owner"], P.SCENARIOS)),
    ("questions", "MVP Demo Questions",
     lambda: "<ol>" + "".join(f"<li>{_esc(q)}</li>" for q in P.DEMO_QUESTIONS) + "</ol>"),
    ("fr", "Functional & Non-Functional Requirements",
     lambda: _table(["ID", "Requirement", "Priority", "Acceptance criteria"], P.FUNC_REQS)
             + _table(["Non-functional area", "Requirement"], P.NON_FUNCTIONAL)),
    ("ui", "UI Output Design & Trace Levels",
     lambda: _table(["UI section", "Content shown"], P.UI_SECTIONS)
             + _table(["Trace level", "Audience", "Content shown"], P.TRACE_LEVELS)),
    ("audit", "Audit Event Schema",
     lambda: _table(["Audit field", "Example", "Purpose"], P.AUDIT_SCHEMA)),
    ("milestones", "Implementation Milestones",
     lambda: _table(["Phase / milestone", "Deliverables", "Exit criteria"], P.MILESTONES)),
    ("risks", "Risks & Mitigations",
     lambda: _table(["Risk", "Mitigation"], P.RISKS)),
    ("readiness", "Implementation-Readiness Checklist",
     lambda: _table(["Question", "Answer"], P.READINESS)),
    ("status", "Prototype Status (this repository)",
     lambda: _table(["Component", "Status", "Notes"], P.PROTOTYPE_STATUS)),
]


def render_html() -> str:
    secs = "".join(_section(i + 1, sid, title, body()) for i, (sid, title, body) in enumerate(SECTIONS))
    toc = "".join(f'<a href="#{sid}" onclick="ensureOpen(\'{sid}\')">{i + 1}. {_esc(title)}</a>'
                  for i, (sid, title, _) in enumerate(SECTIONS))
    return _TEMPLATE.format(title=_esc(P.TITLE), subtitle=_esc(P.SUBTITLE),
                            tagline=_esc(P.TAGLINE), toc=toc, sections=secs)


_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --blue:#2563eb; --ink:#0f172a; --muted:#64748b; --line:#e2e8f0; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
         color:var(--ink); background:#f8fafc; line-height:1.55; }}
  header {{ background:linear-gradient(135deg,#1e3a8a,#2563eb); color:white; padding:34px 24px; }}
  header h1 {{ margin:0 0 4px; font-size:1.9rem; }}
  header p {{ margin:0; opacity:.92; }}
  .wrap {{ display:grid; grid-template-columns:250px 1fr; gap:24px; max-width:1200px;
          margin:20px auto; padding:0 18px; }}
  nav {{ position:sticky; top:18px; align-self:start; background:white; border:1px solid var(--line);
        border-radius:10px; padding:14px; max-height:90vh; overflow:auto; }}
  nav b {{ font-size:.78rem; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }}
  nav a {{ display:block; padding:5px 8px; color:var(--ink); text-decoration:none; border-radius:6px;
          font-size:.86rem; }}
  nav a:hover {{ background:#eff6ff; color:var(--blue); }}
  .card {{ background:white; border:1px solid var(--line); border-radius:10px; margin:0 0 16px; overflow:hidden; }}
  .card h2 {{ margin:0; padding:15px 18px; font-size:1.12rem; cursor:pointer; display:flex;
             align-items:center; gap:10px; user-select:none; }}
  .card h2:hover {{ background:#f1f5f9; }}
  .num {{ background:var(--blue); color:white; min-width:26px; height:26px; border-radius:50%;
         display:inline-grid; place-items:center; font-size:.78rem; }}
  .chev {{ margin-left:auto; color:var(--muted); transition:transform .2s; }}
  .card.collapsed .chev {{ transform:rotate(-90deg); }}
  .body {{ padding:0 18px 18px; }}
  .card.collapsed .body {{ display:none; }}
  table {{ width:100%; border-collapse:collapse; margin:8px 0; font-size:.88rem; }}
  th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ background:#f1f5f9; color:#334155; }}
  .callout {{ padding:12px 14px; border-radius:8px; }}
  .callout.ok {{ background:#dcfce7; border-left:4px solid #16a34a; }}
  .badges {{ margin-top:10px; }}
  .badge {{ display:inline-block; background:#eff6ff; color:var(--blue); border:1px solid #bfdbfe;
           padding:4px 10px; border-radius:999px; font-size:.8rem; margin:2px 6px 2px 0; }}
  .note {{ color:var(--muted); font-size:.86rem; }}
  footer {{ text-align:center; color:var(--muted); padding:24px; font-size:.85rem; }}
  .controls {{ max-width:1200px; margin:14px auto 0; padding:0 18px; }}
  .controls button {{ background:white; border:1px solid var(--line); border-radius:8px;
                     padding:8px 14px; cursor:pointer; margin-right:8px; }}
  @media(max-width:820px){{ .wrap{{grid-template-columns:1fr;}} nav{{position:static;}} }}
</style></head>
<body>
<header><h1>{title}</h1><p>{subtitle}</p><p><em>{tagline}</em></p></header>
<div class="controls"><button onclick="setAll(false)">Expand all</button>
  <button onclick="setAll(true)">Collapse all</button></div>
<div class="wrap"><nav><b>Contents</b>{toc}</nav><main>{sections}</main></div>
<footer>Generated from the detailed project plan · read-only synthetic prototype · free &amp; local stack</footer>
<script>
  function toggle(id){{ document.getElementById(id).classList.toggle('collapsed'); }}
  function ensureOpen(id){{ document.getElementById(id).classList.remove('collapsed'); }}
  function setAll(c){{ document.querySelectorAll('.card').forEach(x=>x.classList.toggle('collapsed', c)); }}
</script>
</body></html>"""


if __name__ == "__main__":
    OUT.write_text(render_html(), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")
