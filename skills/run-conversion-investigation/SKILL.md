---
name: run-conversion-investigation
description: Run the governed conversion-drop investigation (ReAct + conditional ToT beam
  search with the multi-agent analyst team) and read the structured trace.
---
# Run a Conversion Investigation

The flagship workflow: classify → catalog sync gate → retrieve → validate → relate →
baseline → ToT gate → dispatch analyst team (parallel) → critic + beam → evidence gate →
synthesize. Evidence strength is gated on the structural checks (metric + graph + SQL).

## Instructions
1. `from workflows.investigation import run_investigation`
2. `t = run_investigation("Why did digital conversion drop yesterday compared with the prior 7-day average?")`
3. Read: `t["answer"]` (headline, summary, drivers, exec_summary), `t["beam"]` /
   `t["depth1"]` (scored branches), `t["steps"]` (decision log), `t["audit"]` (events).
4. Tune `beam_width`, `depth`, `top_k`, or `inject_failure` to explore behavior.
5. In the app, the **🔬 Live Demo** page streams each step and exposes the trace tabs.

Implementation: `workflows/graph.py` (LangGraph), `skills/tot_skill.py` (scoring), `agents/team.py` (team).
