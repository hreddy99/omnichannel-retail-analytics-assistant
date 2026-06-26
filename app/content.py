"""
Structured product content for the Omnichannel Retail Analytics Assistant -
a governed agentic analytics assistant for the modern data platform. Shared by
the Streamlit app and the standalone interactive HTML so both stay in sync from
a single source.
"""

SUBTITLE = "Governed agentic analytics for the modern data platform"
TAGLINE = "ReAct + RAG + Knowledge Graph + Conditional Tree-of-Thought Beam Search"

EXECUTIVE_SUMMARY = (
    "The Omnichannel Retail Analytics Assistant is a governed multi-agent investigation system, "
    "not a chatbot. It advances conversational analytics from simple natural-language Q&A or "
    "chart generation into a governed investigation workflow. A business user can ask a "
    "natural-language retail question across scattered enterprise data and receive an "
    "evidence-based, owner-routed answer in seconds. Governance is engineered into the workflow: "
    "YAML-certified definitions are the source of truth, retrieval and graph reasoning stay "
    "within approved context, all data access is read-only, the LLM drafts wording only and "
    "never controls the numbers or the decision, and higher-risk findings escalate to human "
    "review. The result is faster, safer, and more consistent decision support. Every answer "
    "includes evidence, caveats, confidence, recommended owner actions, and a full audit trail, "
    "giving the enterprise a repeatable and auditable pattern for agentic AI on a governed data "
    "platform."
)

BUSINESS_PROBLEM = (
    "Large retailers spend significant time, labor, and money answering business questions that "
    "sound simple but require evidence from many disconnected, team-owned systems. A question "
    "such as \"Why did digital conversion drop yesterday?\", \"Which categories have high traffic "
    "but weak conversion?\", \"Are delivery delays increasing customer-service contacts?\", or "
    "\"Why do ecommerce gross sales not reconcile with finance revenue?\" can require clickstream, "
    "orders, inventory, fulfillment, marketing, customer service, finance, product hierarchy, "
    "category ownership, and vendor data. Because this evidence is scattered, teams often spend "
    "hours or days pulling extracts, joining data manually, reconciling definitions, validating "
    "assumptions, and meeting across functions before leaders can act. The cost is not only "
    "analyst time; it is also delayed decisions, slower issue resolution, continued revenue "
    "leakage, and inconsistent explanations across teams.\n\n"
    "AI-enabled analytics tools such as Microsoft Power BI Copilot and Databricks AI/BI Genie show "
    "promise for natural-language analytics, but they do not fully solve complex cross-functional "
    "investigations on their own. Microsoft's own Copilot guidance says Copilot can improve "
    "productivity with semantic models, but it also warns that organizations must prepare the "
    "data, semantic model, and users; otherwise outputs can be low-quality, inaccurate, or "
    "misleading. Databricks Genie Spaces are domain-specific natural-language chat interfaces that "
    "return SQL queries, result tables, and visualizations, but Databricks also describes the need "
    "for curated datasets, SQL examples, business semantics, and organization-specific "
    "instructions. These tools are strong for in-model Q&A and text-to-SQL, but complex retail "
    "investigations still require certified definitions, cross-domain evidence, freshness checks, "
    "causal restraint, auditability, and human validation.\n\n"
    "_Sources: [Power BI Copilot, prepare your data, semantic model, and users (Microsoft "
    "Learn)](https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-semantic-models) · "
    "[AI/BI Genie Spaces (Databricks documentation)](https://docs.databricks.com/aws/en/genie/)._"
    "\n\n"
    "The intended users are merchandising, marketing, finance, fulfillment operations, customer "
    "service, category management, CPG/vendor partners, analysts, and line-of-business leaders. "
    "Leaders need a concise answer and recommended owner actions, while analysts need evidence, "
    "definitions, caveats, freshness status, and an audit trail. The Omnichannel Retail Analytics "
    "Assistant addresses this gap by shortening the path from natural-language question to "
    "governed, evidence-backed, owner-routed answer while preserving traceability and human review."
)

SYSTEM_GOAL_SCOPE = (
    "The system goal is to prove out a governed conversational analytics pattern for enterprise "
    "retail decision support. In many organizations, operational data already lands in a medallion "
    "architecture from Bronze to Silver to Gold and is served through tools such as Power BI, "
    "Databricks AI/BI, or other BI platforms. Those tools are useful for dashboards, semantic-model "
    "Q&A, and text-to-SQL, but complex retail questions often require more than a single chart or "
    "one-shot answer. This project shows how conversational analytics can evolve into a governed "
    "multi-step investigation layer where a business user asks a natural-language question over "
    "scattered enterprise data and receives an evidence-based, owner-routed answer with caveats, "
    "confidence, and traceability. The enterprise pattern is designed to sit on top of the same "
    "governed data platform and semantic layer, using certified Silver and Gold data products or "
    "governed read-in-place federation "
    "through tools such as Lakehouse Federation, Unity Catalog foreign catalogs, or Trino. The key "
    "requirement is governance, not physical data location. The assistant complements BI tools "
    "rather than replacing them by adding the investigation workflow that turns what happened into "
    "why it happened, with evidence, accountable owners, and human review.\n\n"
    "The scope is intentionally bounded for safety and feasibility. The prototype runs locally "
    "with synthetic fixed-seed data only. It does not connect to or update production ERP, OMS, "
    "CRM, pricing, inventory, campaign, fulfillment, finance, or customer-service systems. It "
    "demonstrates the enterprise pattern using local free tools: Python, Streamlit, LangGraph, "
    "DuckDB, YAML, ChromaDB, sentence-transformers, NetworkX, Ollama/qwen2.5, and deterministic "
    "Python guardrails."
)

# (role, typical question, assistant value)
BUSINESS_ROLES = [
    ("Marketing", "Did a campaign drive traffic that converted below normal?",
     "Compares channel/campaign traffic mix, conversion, and contribution to the drop."),
    ("Merchandising", "Which categories had high traffic but low conversion?",
     "Combines category traffic, sales, availability, stockout pressure, owner routing."),
    ("Fulfillment operations", "Did fulfillment delays or reduced options hurt conversion?",
     "Checks option availability, promise delays, cancellations, affected regions."),
    ("Customer service", "Did operational issues increase contacts?",
     "Links service contacts to fulfillment, inventory, order, and cancellation signals."),
    ("Finance", "Why does ecommerce sales not match finance revenue?",
     "Explains gross-to-net caveats: returns, timing, tax, shipping, adjustments."),
    ("Business leaders", "What happened and what should we investigate next?",
     "Concise evidence-backed summary with caveats, confidence, and action owners."),
]

# Enterprise analytics & modern data platform alignment ----------------------
ENTERPRISE_ALIGNMENT = (
    "The assistant represents a practical enterprise analytics pattern for using "
    "agentic AI on top of a governed modern data platform. In production it sits "
    "above certified analytical data products and helps users investigate "
    "performance questions without needing to know every source table, metric rule, "
    "or operational-system caveat. It translates natural-language questions into "
    "governed analytical steps: retrieve the certified metric definition, identify "
    "approved sources, check freshness and grain, validate SQL, run read-only "
    "analysis, and synthesize evidence into a business explanation, complementing "
    "data warehouses, lakehouses, semantic models, and BI dashboards."
)

# Medallion architecture mapping (layer, role)
MEDALLION = [
    ("Bronze", "Raw data lands from operational systems (ecommerce clickstream, OMS, ERP inventory, fulfillment, campaign, finance, service), preserving source detail and traceability."),
    ("Silver", "Cleaned, standardized, conformed analytical tables: sessions, events, orders, order items, product, category, inventory, fulfillment, campaign daily, service contacts, finance daily, returns, vendor scorecard, region/vendor/contact-reason dimensions."),
    ("Gold", "Business-ready metrics and data products: digital conversion, sales performance, inventory availability, fulfillment delay rate, campaign conversion, gross-to-net bridge, margin proxy, return rate, vendor scorecard, contact trends."),
]
MEDALLION_NOTE = (
    "The assistant primarily queries curated Silver and Gold data. The YAML semantic "
    "catalog is the governance layer that defines which metrics are certified, which "
    "tables are allowed, what grain is valid, how joins work, how fresh the data is, "
    "and what caveats must appear in the final response."
)

# Relationship to surrounding OLTP systems (system, analytics role, assistant use)
OLTP_RELATIONSHIP = [
    ("Ecommerce platform", "Sessions, carts, checkout events, digital orders", "Analyze traffic, funnel behavior, and conversion"),
    ("OMS", "Order status, cancellations, fulfillment type", "Explain order and conversion impacts"),
    ("ERP / Inventory", "Product availability, store inventory, vendor data", "Investigate stockouts and availability issues"),
    ("Fulfillment systems", "Promise dates, delivery delays, pickup availability", "Identify fulfillment-related conversion drivers"),
    ("Campaign platforms", "Campaign traffic, spend, attribution", "Evaluate whether traffic converted below normal"),
    ("CRM / Customer service", "Contact volume, reason codes, order issues", "Connect service spikes to operational issues"),
    ("Finance systems", "Revenue, returns, tax, shipping, adjustments", "Reconcile ecommerce and financial reporting"),
]

ENTERPRISE_VALUE = [
    "Reduces time spent manually tracing root causes across dashboards, source systems, and teams.",
    "Improves trust by forcing answers to reference certified definitions, approved grains, evidence, caveats, freshness, and confidence.",
    "Turns dashboards into guided investigations (e.g. 'compare by fulfillment type', 'drill into top categories').",
    "Creates a repeatable pattern for governed AI over analytical data products without unsafe write access to operational systems.",
]

# Agentic capability alignment (capability, how the assistant implements it, what good looks like)
CAPABILITY_ALIGNMENT = [
    ("Tool calling",
     "Calls semantic search, YAML validation, graph traversal, SQL validation, DuckDB queries, profiling, evidence scoring, and action-log functions.",
     "Debug trace shows tools called in logical order with outputs in the final answer."),
    ("Reasoning loop / ReAct",
     "LangGraph coordinates plan, retrieve, validate, act, observe, revise, answer.",
     "Agent recovers from ambiguity, stale data, wrong grain, weak evidence, or conflict."),
    ("Knowledge and memory",
     "ChromaDB retrieves chunks, caveats, templates, examples, notes; workflow state holds investigation context.",
     "Final answer shows definition, retrieved context, graph path, evidence basis."),
    ("Further reasoning / ToT",
     "Conditional beam search explores competing driver hypotheses before selecting findings.",
     "System shows candidate branches, scores, pruning, survivors, and selection logic."),
    ("Multi-agent coordination",
     "Roles cover semantic lookup, graph reasoning, SQL analysis, and domain interpretation.",
     "At least one specialized agent executes a tool-backed task feeding synthesis."),
    ("Safety",
     "Read-only, synthetic, guarded against unsupported claims or unsafe actions.",
     "No writes; weak findings labeled possible, hypothesis, or inconclusive."),
]


# Architecture layers (layer, component, responsibility, control)
ARCH_LAYERS = [
    ("Interface", "Streamlit", "Accept questions; show evidence, trust, debug trace, action log.", "Display-only; no data writes."),
    ("Orchestration", "LangGraph", "State, tool calls, branch decisions, budget, stopping, synthesis.", "Central controller; all tool calls via nodes."),
    ("Source of truth", "YAML catalog", "Metrics, grains, joins, filters, caveats, freshness, owners, guardrails.", "version, last_updated, content_hash."),
    ("Retrieval", "ChromaDB", "Retrieve top-k chunks from YAML and approved notes.", "Reject stale chunks; validate vs YAML."),
    ("Graph reasoning", "NetworkX", "Traverse metric-table-driver-owner relationships.", "Generated from YAML; version mismatch -> rebuild/block."),
    ("Further reasoning", "ToT beam search", "Explore competing driver paths; prune weak branches.", "Conditional; beam width 2, depth limit 2."),
    ("Analysis", "DuckDB", "Run read-only evidence queries over synthetic data.", "SELECT-only; approved templates."),
    ("Safety", "Guardrails", "Block unsafe SQL, stale sources, unsupported causes, writes.", "Deterministic Python checks."),
    ("Output", "Final answer + action log", "Summarize findings, caveats, confidence, owners.", "Human-reviewed recommendation only."),
]

# YAML catalog files (file, contents, used by)
YAML_FILES = [
    ("metrics.yaml", "Metric name, definition, numerator/denominator, formula, grain, filters, approved tables, caveats, owner, examples.", "Retrieval, source gate, final definition."),
    ("tables.yaml", "Table descriptions, grain, keys, allowed joins, freshness, data-quality notes.", "SQL validator, graph generation, planning."),
    ("drivers.yaml", "Business drivers: campaign mix, stockout, fulfillment delay, funnel, service, finance.", "Graph nodes, ToT candidates, owner routing."),
    ("business_rules.yaml", "Required filters, date logic, comparison windows, baseline definitions.", "SQL templates, validation, caveats."),
    ("guardrails.yaml", "SELECT-only, stale warnings, confidence thresholds, source priority.", "Guardrail functions, response template."),
    ("examples.yaml", "Approved analysis plans, SQL templates, expected evidence patterns.", "ChromaDB retrieval, SQL fallback."),
    ("versions.yaml", "Catalog version, file hash, section ID, last_updated, approved flag.", "Catalog sync/version gate."),
]

# Graph objects (object, examples, purpose)
GRAPH_OBJECTS = [
    ("Metric nodes", "Digital Conversion, Inventory Availability, Fulfillment Delay Rate, Campaign Conversion.", "Governed business measures."),
    ("Table nodes", "fact_sessions, fact_orders, fact_inventory_daily, fact_fulfillment, dim_campaign, dim_product.", "Approved evidence sources."),
    ("Driver nodes", "Campaign Mix Shift, Inventory Stockout, Fulfillment Constraint, Funnel Drop-off, Service Spike, Finance Caveat.", "Hypotheses / evidence paths."),
    ("System nodes", "Ecommerce, OMS, ERP Inventory, Fulfillment Platform, Campaign Platform, Service, Finance.", "Enterprise context (no real connections)."),
    ("Owner nodes", "Marketing, Merchandising, Fulfillment Ops, Customer Service, Finance, Digital Analytics.", "Route action-log recommendations."),
    ("Edges", "uses, has_grain, affects, measured_by, owned_by, feeds_table, requires_filter, caveated_by.", "Select evidence paths; support explanation."),
]

# Agent roles (role, purpose, tools, output)
AGENT_ROLES = [
    ("Analytics Orchestrator", "Controls workflow, state, budget, stopping, ToT trigger, response.", "LangGraph, tool registry.", "Investigation plan, branch decisions, final answer."),
    ("Semantic Agent", "Retrieves definitions, caveats, examples, table rules, SQL templates.", "ChromaDB, YAML parser.", "Certified definition and approved tables."),
    ("Catalog Sync Agent", "Checks YAML version/hash against ChromaDB and NetworkX.", "Hash utils, Chroma/graph metadata.", "Stale chunks/edges refreshed or blocked."),
    ("Graph Reasoning Agent", "Finds related drivers, tables, systems, owners.", "NetworkX.", "Evidence checklist and owner routing."),
    ("ToT Thought Generator", "Creates candidate driver branches for high-branching cases.", "LangGraph node, schema-constrained gen.", "Candidate thoughts per domain."),
    ("Critic / Evaluator", "Scores branches on source + evidence criteria.", "Heuristics, YAML/graph/SQL/DuckDB checks.", "Branch scores, pruning, tie-breaks."),
    ("SQL Analyst Agent", "Creates/validates SQL, executes read-only queries.", "Templates, SQL validator, DuckDB.", "Evidence tables vs baseline."),
    ("Synthesis Agent", "Ranks supported drivers, writes final response.", "Result summaries, confidence rules.", "Definition, findings, caveats, owners."),
]

# ---------------------------------------------------------------------------
# Multi-agent system - deliberate design decisions
# ---------------------------------------------------------------------------
MULTI_AGENT_INTRO = (
    "The domain investigations are run by a TEAM of specialized AI agents that "
    "collaborate under an Orchestrator. Multi-agent design is a deliberate choice: "
    "it unlocks capability through specialization (each analyst owns one domain, its "
    "tables, metric, and guardrails) and parallelism (independent read-only queries "
    "run concurrently). It is used only when it pays for itself."
)

# Specialized analyst team (analyst, domain, governed driver / focus)
ANALYST_TEAM = [
    ("Marketing Analyst", "marketing", "campaign_mix, channel/campaign traffic mix & conversion"),
    ("Merchandising Analyst", "merchandising", "inventory_availability, stockout vs views"),
    ("Fulfillment Analyst", "fulfillment", "fulfillment_constraints, delays & option availability"),
    ("Digital Analytics Analyst", "analytics", "funnel_behavior, cart→purchase by category/device"),
    ("Customer Service Analyst", "service", "service_signal, contact spike by reason code"),
    ("Finance Analyst", "finance", "finance_caveat, gross-to-net reconciliation"),
    ("Vendor / Category Analyst", "merchandising", "vendor_insight, sales-weighted stockout by vendor"),
]

# When to use / not use multiple agents (decision, rationale)
MULTI_AGENT_WHEN = [
    ("Use the team", "Question is cross-domain and the ToT gate confirms competing drivers; dispatch the specialized analysts whose domain is relevant."),
    ("Use a single analyst", "Narrow, single-domain question, no team is formed; avoids coordination overhead."),
    ("Run agents in parallel", "Domain queries are independent and read-only, so they execute concurrently to cut wall-clock latency."),
    ("Keep the Critic central", "One Critic scores all analysts on the same rubric, so specialization never means inconsistent standards."),
]

# Trade-offs accepted and mitigations (trade-off, mitigation)
MULTI_AGENT_TRADEOFFS = [
    ("Coordination overhead", "Bounded thread pool + fixed per-agent timeout; each agent makes exactly one read-only query."),
    ("Added complexity", "All agents share one contract (DomainAgent.analyze → AgentResult) and one governed catalog; behavior stays uniform and inspectable."),
    ("New failure modes (slow/failing/disagreeing agents)", "Each agent is isolated (own DuckDB cursor, try/except, timeout); a failure degrades to an excluded result; the Critic and source-priority rules resolve disagreement (DuckDB evidence + YAML win)."),
    ("Non-determinism from parallelism", "The Critic re-sorts results deterministically (score, then evidence strength), so output is stable regardless of completion order."),
    ("Observability gap", "A coordination log records which agents ran, durations, parallel speedup, and failures; every agent call is an audit event."),
]


# Source-conflict rules (situation, decision, behavior)
CONFLICT_RULES = [
    ("ChromaDB definition conflicts with YAML", "YAML wins (governed truth).", "States certified definition or asks clarification."),
    ("ChromaDB chunk is stale vs YAML", "Reject and re-embed before use.", "If refresh fails, answer incomplete or ask clarification."),
    ("NetworkX relationship conflicts with YAML", "YAML wins; graph regenerated/flagged.", "Avoids disputed path or discloses uncertainty."),
    ("Example SQL suggests unsupported table", "SQL validator blocks unless YAML-approved.", "Revises plan before querying."),
    ("DuckDB evidence does not support hypothesis", "DuckDB evidence controls the claim.", "Labels hypothesis inconclusive."),
    ("Multiple valid definitions exist", "Ask clarification or use documented default.", "States exact definition used."),
    ("Prior note suggests a repeated pattern", "Treat as context only, not evidence.", "Current DuckDB must confirm before it is a finding."),
]


DEMO_QUESTIONS = [
    # Flagship cross-domain investigation
    "Why did digital conversion drop yesterday compared with the prior 7-day average?",
    # Each functional analyst answering a realistic question from its own perspective
    "Marketing: how did our paid social campaigns perform yesterday?",
    "Merchandising: which categories had stockouts hurting availability yesterday?",
    "Fulfillment: are delivery delays or reduced options worse in any region?",
    "Digital Analytics: where are shoppers dropping off in the checkout funnel?",
    "Customer Service: did support contacts spike yesterday, and why?",
    "Merchandising: which vendor or category partner should we alert about stockouts?",
    "Finance: why doesn't ecommerce sales match finance net revenue?",
    # Cross-cutting
    "What actions should each team take next?",
    "What caveats or data-freshness limits should I know before trusting this result?",
]

# Cross-functional briefing questions: these fan out the WHOLE analyst team in
# parallel (the multi-agent path) and return a ranked, owner-routed executive
# briefing across every domain, not the single conversion-drop narrative.
BRIEFING_QUESTIONS = [
    "Give me an executive briefing on the biggest issues across the business yesterday.",
    "Across all teams, what are the top cross-functional risks we should act on now?",
    "Brief leadership on where to focus across marketing, merchandising, fulfillment, and service.",
]

# Edge-case scenario: two drivers come back equally supported. Selecting this runs the
# full conversion investigation with an equal-strength tie forced between the top two
# drivers (Electronics stockout vs West fulfillment delays), so the deterministic
# tie-break sequence and its escalation are demonstrated.
TIE_SCENARIO_QUESTION = ("Yesterday's conversion drop, Merchandising blames the Electronics "
                         "stockout, Fulfillment blames the West delivery delays. Which is the "
                         "real driver, and what do we fix first?")

# Edge-case scenario: a governed source is stale (a YAML edit not yet re-embedded). The
# version/hash sync gate detects the drift, flags it for refresh (YAML wins), and routes
# the run to human review instead of answering on stale context.
STALE_SCENARIO_QUESTION = ("Give me yesterday's conversion-drop drivers, we need to act on "
                           "this in the leadership standup this morning.")
