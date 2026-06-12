"""
Graphviz DOT diagrams rendered in-app via st.graphviz_chart (client-side viz.js,
no system Graphviz needed). Architecture, business flow, tool flow, reasoning flow,
multi-agent flow, and the data model / medallion view.
"""

ARCHITECTURE = """
digraph G {
  rankdir=TB; node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=10];
  ui [label="Streamlit UI\\n(questions, evidence, trust, audit)" fillcolor="#dbeafe"];
  orch [label="LangGraph Orchestrator\\n(state machine, routing, budget, stopping)" fillcolor="#bfdbfe"];
  yaml [label="YAML Catalog\\n(source of truth: metrics/tables/drivers/guardrails)" fillcolor="#fef9c3"];
  chroma [label="ChromaDB + sentence-transformers\\n(governed retrieval)" fillcolor="#dcfce7"];
  graph [label="NetworkX graph\\n(metric→driver→table→owner)" fillcolor="#dcfce7"];
  duck [label="DuckDB\\n(read-only evidence over synthetic data)" fillcolor="#e9d5ff"];
  guard [label="Guardrails\\n(SQL safety, freshness, conflict, write-refusal)" fillcolor="#fee2e2"];
  llm [label="Ollama LLM (optional)\\n(drafting only — never source of truth)" fillcolor="#f1f5f9"];
  ui -> orch;
  orch -> yaml; orch -> chroma; orch -> graph; orch -> duck; orch -> guard; orch -> llm;
  chroma -> yaml [style=dashed label="validated against" fontsize=8];
  graph -> yaml [style=dashed label="generated from" fontsize=8];
  orch -> ui [label="grounded answer + audit" fontsize=8];
}
"""

BUSINESS_FLOW = """
digraph G {
  rankdir=LR; node [shape=box style="rounded,filled" fillcolor="#dbeafe" fontname="Helvetica" fontsize=10];
  q [label="Business question\\n(natural language)"];
  cls [label="Classify intent\\n(investigation / analytics / themed)"];
  gov [label="Resolve governed\\ndefinition + sources"];
  eval [label="Run read-only\\nevidence"];
  syn [label="Grounded answer\\n+ confidence + caveats"];
  act [label="Owner-routed\\nrecommendation" fillcolor="#dcfce7"];
  hum [label="Human review\\n(no system writes)" fillcolor="#fee2e2"];
  q -> cls -> gov -> eval -> syn -> act -> hum;
}
"""

TOOL_FLOW = """
digraph G {
  rankdir=LR; node [shape=box style="rounded,filled" fillcolor="#e0f2fe" fontname="Helvetica" fontsize=10];
  a [label="Semantic search\\n(ChromaDB)"]; b [label="YAML validate"]; c [label="Graph traverse\\n(NetworkX)"];
  d [label="SQL validate\\n(guardrail)"]; e [label="DuckDB execute"]; f [label="Evidence score\\n(Critic rubric)"];
  g [label="Synthesize\\n(+ optional LLM)"]; h [label="Audit log"];
  a -> b -> c -> d -> e -> f -> g; g -> h [style=dashed];
}
"""

REASONING_FLOW = """
digraph G {
  rankdir=TB; node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=10 fillcolor="#bfdbfe"];
  start [label="Validated question (depth 0)\\nmetric, window, budget" fillcolor="#fef9c3"];
  gate [label="ToT trigger?\\n(competing drivers + material drop)" shape=diamond fillcolor="#fde68a"];
  linear [label="Single path\\n(no beam)" fillcolor="#f1f5f9"];
  d1 [label="Depth 1: candidate driver branches\\n(campaign / inventory / fulfillment / funnel …)"];
  score [label="Critic scores 0–14\\nprune < 7"];
  beam [label="Beam keeps top 2"];
  d2 [label="Depth 2: sub-driver refinement"];
  stop [label="Evidence gate + stopping\\n(budget, threshold)" fillcolor="#dcfce7"];
  ans [label="Grounded answer" fillcolor="#dcfce7"];
  start -> gate; gate -> linear [label="no" fontsize=8]; gate -> d1 [label="yes" fontsize=8];
  d1 -> score -> beam -> d2 -> stop; linear -> stop; stop -> ans;
}
"""

MULTI_AGENT_FLOW = """
digraph G {
  rankdir=TB; node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=10];
  orch [label="Analytics Orchestrator" fillcolor="#bfdbfe"];
  subgraph cluster_team { label="Specialized analysts (parallel)"; style=dashed; color="#94a3b8";
    m [label="Marketing" fillcolor="#dcfce7"]; me [label="Merchandising" fillcolor="#dcfce7"];
    fu [label="Fulfillment" fillcolor="#dcfce7"]; da [label="Digital Analytics" fillcolor="#dcfce7"];
    cs [label="Customer Service" fillcolor="#dcfce7"]; fi [label="Finance" fillcolor="#dcfce7"];
    ve [label="Vendor/Category" fillcolor="#dcfce7"]; }
  critic [label="Critic / Evaluator\\n(score, prune, beam)" fillcolor="#fde68a"];
  syn [label="Synthesis + Executive Summary" fillcolor="#dbeafe"];
  orch -> m; orch -> me; orch -> fu; orch -> da; orch -> cs; orch -> fi; orch -> ve;
  m -> critic; me -> critic; fu -> critic; da -> critic; cs -> critic; fi -> critic; ve -> critic;
  critic -> syn;
}
"""

DATA_MODEL = """
digraph G {
  rankdir=LR; node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=9];
  subgraph cluster_b { label="Bronze (raw)"; style=filled; color="#fef3c7";
    src [label="Operational systems\\n(ecommerce, OMS, ERP, fulfillment,\\ncampaign, finance, service)" fillcolor="#fde68a"]; }
  subgraph cluster_s { label="Silver (conformed facts/dims)"; style=filled; color="#e0f2fe";
    fs [label="fact_sessions"]; fe [label="fact_events"]; fo [label="fact_orders"];
    foi [label="fact_order_items"]; fi [label="fact_inventory_daily"]; ff [label="fact_fulfillment"];
    fc [label="fact_customer_contacts"]; ffd [label="fact_finance_daily"];
    dp [label="dim_product"]; dc [label="dim_category"]; dk [label="dim_campaign"]; }
  subgraph cluster_g { label="Gold (metrics / data products)"; style=filled; color="#dcfce7";
    gm [label="digital conversion, stockout rate,\\nfulfillment delay, net revenue,\\ncontact trends" fillcolor="#bbf7d0"]; }
  src -> fs; src -> fo;
  fo -> foi; foi -> dp; dp -> dc; fs -> dk; fi -> dc; fe -> fs;
  fs -> gm; fo -> gm; fi -> gm; ff -> gm; ffd -> gm; fc -> gm;
}
"""

DIAGRAMS = [
    ("System architecture", "How the layers fit together; YAML governs truth, the LLM never does.", ARCHITECTURE),
    ("Business flow", "From a natural-language question to a human-reviewed, owner-routed recommendation.", BUSINESS_FLOW),
    ("Tool flow", "The order tools are called within a governed investigation.", TOOL_FLOW),
    ("Reasoning flow (ReAct + conditional ToT)", "When the bounded beam search activates and how branches are scored/pruned.", REASONING_FLOW),
    ("Multi-agent flow", "The Orchestrator dispatches specialized analysts in parallel; the Critic ranks; Synthesis composes.", MULTI_AGENT_FLOW),
    ("Data model (medallion)", "Bronze → Silver (fact/dim) → Gold metrics that the assistant queries.", DATA_MODEL),
]
