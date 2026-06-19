"""
Structured product content for the Omnichannel Retail Analytics Assistant -
a governed agentic analytics assistant for the modern data platform. Shared by
the Streamlit app and the standalone interactive HTML so both stay in sync from
a single source.
"""

SUBTITLE = "Governed agentic analytics for the modern data platform"
TAGLINE = "ReAct + RAG + Knowledge Graph + Conditional Tree-of-Thought Beam Search"

FEASIBILITY = (
    "This project is intentionally scoped to be free, local, read-only, and doable "
    "on a personal PC. The MVP uses Python, Streamlit, LangGraph, DuckDB, YAML files, "
    "ChromaDB, sentence-transformers, NetworkX, Ollama, and custom guardrail "
    "functions. No paid cloud services, enterprise data, proprietary systems, "
    "production connectors, or write access are required."
)

EXECUTIVE_SUMMARY = (
    "The Omnichannel Retail Analytics Assistant is a governed agentic research "
    "assistant that investigates retail performance questions across digital "
    "behavior, orders, campaigns, inventory, fulfillment, service, finance, and "
    "category/vendor context. The assistant focuses on: why did digital conversion "
    "drop yesterday compared with the prior 7-day average? It is not a generic "
    "chatbot - it is a structured investigation workflow. LangGraph controls the "
    "reasoning state and tool calls; YAML is the authoritative source of truth; "
    "ChromaDB retrieves catalog context; NetworkX maps relationships; DuckDB "
    "produces evidence from synthetic data; guardrails enforce read-only SQL, "
    "freshness, source conflicts, evidence thresholds, and guarded language. "
    "It adds a conditional Tree-of-Thought layer (bounded beam search) activated "
    "only when multiple plausible driver paths compete."
)

BUSINESS_PROBLEM = (
    "Retail leaders ask simple questions whose answers span many systems. "
    "\"Why did digital conversion drop yesterday?\" may require sessions, events, "
    "orders, inventory availability, fulfillment options, campaign mix, "
    "product/category behavior, service signals, finance caveats, and certified "
    "metric definitions. A prompt-only LLM is unreliable: it may use a generic "
    "definition, ignore table grain, compare stale data, or invent a root cause. "
    "The assistant grounds each answer in governed context and query evidence first."
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
    "governed analytical steps - retrieve the certified metric definition, identify "
    "approved sources, check freshness and grain, validate SQL, run read-only "
    "analysis, and synthesize evidence into a business explanation - complementing "
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
    ("Marketing Analyst", "marketing", "campaign_mix — channel/campaign traffic mix & conversion"),
    ("Merchandising Analyst", "merchandising", "inventory_availability — stockout vs views"),
    ("Fulfillment Analyst", "fulfillment", "fulfillment_constraints — delays & option availability"),
    ("Digital Analytics Analyst", "analytics", "funnel_behavior — cart→purchase by category/device"),
    ("Customer Service Analyst", "service", "service_signal — contact spike by reason code"),
    ("Finance Analyst", "finance", "finance_caveat — gross-to-net reconciliation"),
    ("Vendor / Category Analyst", "merchandising", "vendor_insight — sales-weighted stockout by vendor"),
]

# When to use / not use multiple agents (decision, rationale)
MULTI_AGENT_WHEN = [
    ("Use the team", "Question is cross-domain and the ToT gate confirms competing drivers; dispatch the specialized analysts whose domain is relevant."),
    ("Use a single analyst", "Narrow, single-domain question — no team is formed; avoids coordination overhead."),
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
    "Show the certified definition and evidence path behind this answer.",
    "What caveats or data-freshness limits should I know before trusting this result?",
]

# Cross-functional briefing questions: these fan out the WHOLE analyst team in
# parallel (the multi-agent path) and return a ranked, owner-routed executive
# briefing across every domain — not the single conversion-drop narrative.
BRIEFING_QUESTIONS = [
    "Give me an executive briefing on the biggest issues across the business yesterday.",
    "Across all teams, what are the top cross-functional risks we should act on now?",
    "Brief leadership on where to focus across marketing, merchandising, fulfillment, and service.",
]


# This prototype's status vs the plan (component, status, note)
PROTOTYPE_STATUS = [
    ("Faker synthetic data + seeded scenarios", "Built", "data/generator.py: 18-table fact_/dim_ model (Phase II/III: returns, campaign daily, vendor scorecard, margin proxy, region/vendor/contact-reason dims), 40+1 days, seeded scenarios, eval-only answer key."),
    ("Data validation (section 14.4)", "Built", "evals/validation.py: all checks pass, drop in 15-25% band."),
    ("Split YAML catalog + version manifest", "Built", "catalog/*.yaml with per-file content hashes."),
    ("ChromaDB + sentence-transformers retrieval", "Built", "skills/retrieval_skill.py: real Chroma; ST->ONNX->hashing fallback; sync gate."),
    ("NetworkX graph from YAML", "Built", "skills/graph_skill.py: metric/table/system/driver/owner + edge types; version+hash gate."),
    ("LangGraph workflow", "Built", "workflows/graph.py: real StateGraph, 10 nodes, ReAct loop."),
    ("Conditional ToT beam search", "Built", "skills/tot_skill.py: width 2, depth 2, rubric, pruning, budget, governance pre-screen."),
    ("Multi-agent team", "Built", "agents/team.py: specialized analysts, parallel dispatch, coordination log, graceful degradation; full team + executive summary."),
    ("Guardrails (SQL/freshness/conflict/write)", "Built", "skills/sql_skill.py driven by guardrails.yaml."),
    ("Audit trail + action log", "Built", "skills/audit_skill.py: run_id, section-17.2 event schema, human-reviewed actions."),
    ("Multi-tab UI + 4 trace levels", "Built", "app.py: Answer/Evidence/Trust/ToT/Audit/Action tabs."),
    ("Ollama LLM drafting", "Optional", "skills/llm_skill.py: used if a daemon is reachable; deterministic fallback otherwise."),
]
