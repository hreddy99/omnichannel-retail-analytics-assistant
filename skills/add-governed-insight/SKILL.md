---
name: add-governed-insight
description: Add a new direct analytics insight question (a single governed read-only query
  with a numeric summary and chart). Use when adding a non-conversion lookup to the demo.
---
# Add a Governed Analytics Insight

Insights are standalone analytics answers (not the conversion investigation). Each is one
read-only query over approved tables plus a numeric summarizer and a chart spec.

## Instructions
1. In `src/insights.py`, add an `Insight(id, question, domain, owner, sql, summarize)` to
   `INSIGHTS`. The SQL must pass `guardrails.check_sql` (SELECT-only, approved tables).
2. Write a `summarize(df)` returning `{headline, summary, metrics:[(label,val)]}` with
   formatted numbers.
3. Add a chart spec to `CHART_SPECS[id]` (`{kind, x, y, title}`); `bar` or `line`.
4. The classifier and the `n_analytics` workflow node route it automatically; it appears
   in the Live Demo dropdown under "Direct analytics questions".
5. Verify: `python -c "from src.insights import run; ..."` and the AppTest smoke checks.

Reference implementations: the 11 existing insights in `src/insights.py`.
