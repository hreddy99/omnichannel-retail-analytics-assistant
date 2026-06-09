"""
Structured product content for the Omnichannel Retail Analytics Assistant -
a governed agentic analytics assistant for the modern data platform. Shared by
the Streamlit app and the standalone interactive HTML so both stay in sync from
a single source.
"""

TITLE = "Omnichannel Retail Analytics Assistant"
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
    ("Silver", "Cleaned, standardized, conformed analytical tables: sessions, events, orders, order items, product, category, inventory, fulfillment, campaign, service contacts, finance daily."),
    ("Gold", "Business-ready metrics and data products: digital conversion, sales performance, inventory availability, fulfillment delay rate, campaign conversion, net revenue, contact trends."),
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

# Capability roadmap (stage, objective, scope, success)
PHASE_ROADMAP = [
    ("Core (current release)", "Deliver the digital conversion investigation assistant.",
     "Conversion, campaign/channel mix, inventory, fulfillment; synthetic data; YAML; ChromaDB; NetworkX; DuckDB; LangGraph; conditional ToT.",
     "End-to-end local demo answers the drop with evidence, caveats, confidence, owner actions."),
    ("Operations & service", "Expand into retail operations and service intelligence.",
     "Service contacts, fulfillment-service linkage, category drilldowns, checkout funnel, regional analysis.",
     "Connects service, fulfillment, category, funnel evidence without overstating causality."),
    ("Finance & vendor", "Expand into finance, vendor insights, and executive summaries.",
     "Finance reconciliation, gross-to-net, vendor/category, returns/margin proxy, executive summaries.",
     "Produces finance-safe, executive-friendly summaries from evidence-backed findings."),
    ("Future production", "Move to governed enterprise deployment after the pattern is proven.",
     "BI semantic layers, RBAC, audit logging, lineage, human-in-the-loop, optional Neo4j.",
     "Architecture remains governed, auditable, and human-reviewed."),
]

# (tool, role, free?, mvp notes)
TOOL_STACK = [
    ("Python", "Runtime, data generator, tool wrappers, validation utilities.", "Yes", "Local virtual environment."),
    ("Streamlit", "UI: question, answer, evidence, trust details, debug trace, action log.", "Yes", "Runs locally in browser."),
    ("LangGraph", "Central controller: state, routing, tool calls, budget, stopping.", "Yes", "Deterministic nodes for each step."),
    ("Ollama", "Local LLM for planning, summarization, response drafting.", "Optional", "Lightweight model; optional with fallback."),
    ("YAML", "Governed source of truth: metrics, tables, rules, caveats, guardrails.", "Yes", "Inspectable, versionable, hashable."),
    ("ChromaDB", "Local vector DB for semantic retrieval over YAML chunks.", "Yes", "Persistent dir; refresh on YAML change."),
    ("sentence-transformers", "Local embedding model for vector search.", "Yes", "all-MiniLM-L6-v2."),
    ("NetworkX", "Local knowledge graph for metric-table-driver-owner.", "Yes", "Python library; no server."),
    ("DuckDB", "Local read-only analytics engine over synthetic tables.", "Yes", "File-based; fast for demo data."),
    ("Python guardrails", "SQL safety, freshness, conflict, evidence, scoring, stopping.", "Yes", "Deterministic, testable functions."),
    ("CrewAI", "Potential future role-based agent framework.", "Optional", "Future option only; not required."),
    ("MCP", "Potential future shared context/state protocol.", "Optional", "Not needed for local MVP."),
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

# ToT depth model (element, definition)
TOT_DEPTH = [
    ("Thought", "A candidate driver hypothesis plus an evidence plan."),
    ("Node", "Reasoning state: metric, source versions, candidate driver, expected evidence, SQL template, score, caveats."),
    ("Branch", "Path from root question to a candidate driver and sub-driver investigation."),
    ("Depth 0", "Validated root question: metric, time window, source versions, query budget."),
    ("Depth 1", "Primary driver branches: campaign mix, inventory, fulfillment, funnel, service, finance, vendor."),
    ("Depth 2", "Sub-driver refinement: paid social quality, category stockout, delivery delay, etc."),
    ("Branching factor", "Usually 3-4 primary branches."),
    ("Depth limit", "Depth 2 for the MVP to avoid branch explosion on a laptop."),
]

# ToT scoring rubric (criterion, max)
TOT_RUBRIC = [
    ("Metric definition validated against YAML", 2),
    ("Approved graph path exists", 2),
    ("SQL safety and template validity", 2),
    ("DuckDB evidence strength", 3),
    ("Freshness and row quality", 2),
    ("Business relevance / actionability", 2),
    ("Caveats manageable", 1),
]
TOT_THRESHOLDS = (
    "Below 7: prune branch or label inconclusive. 7-9: possible contributor (secondary "
    "finding with caveat). 10+: likely driver if evidence is consistent and source checks "
    "pass. Ties: prefer stronger DuckDB evidence, fewer caveats, fresher data, clearer "
    "owner action. Beam width 2. Query budget: 1 baseline + up to 3 driver-path + 1 follow-up."
)

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

# Synthetic tables (table, grain, role)
SYNTH_TABLES = [
    ("fact_sessions", "session", "Traffic, channel, device, campaign, region; conversion denominator."),
    ("fact_events", "event", "Product views, cart adds, checkout starts, purchases (funnel)."),
    ("fact_orders", "order", "Completed eligible orders, status, fulfillment type; conversion numerator."),
    ("fact_order_items", "order item", "Product/category sales and item-level drilldowns."),
    ("fact_inventory_daily", "product-location-day", "Stockout flag, available-online flag, inventory pressure."),
    ("fact_fulfillment", "order-fulfillment", "Promise/actual date, delay days, cancellations, fulfillment type."),
    ("fact_customer_contacts", "contact", "Contact reason, channel, resolution, order link."),
    ("fact_finance_daily", "date/channel/category", "Gross sales, net revenue, returns, tax, shipping."),
    ("dim_product", "product", "SKU, category, brand, price band, vendor_id, partner flag."),
    ("dim_category", "category", "Department, category hierarchy, owner."),
    ("dim_campaign", "campaign", "Campaign name, channel, date range, spend, audience, owner."),
]

# Seeded scenarios (scenario, pattern, expected evidence, owner)
SCENARIOS = [
    ("Digital conversion drop", "Yesterday conversion declines 15-25% vs prior 7-day average.", "Overall delta and contribution ranking show the drop.", "Analytics / Leadership"),
    ("Paid social traffic shift", "Paid social sessions spike but convert below baseline.", "Channel tables show higher traffic share, lower conversion.", "Marketing"),
    ("Inventory availability issue", "Selected categories: high product views, low available-online / high stockout.", "High traffic, low conversion, elevated stockout rate.", "Merchandising"),
    ("Fulfillment constraint", "Delivery delays or fewer options in selected regions.", "Higher delay_days, cancellations, lower option availability.", "Fulfillment Operations"),
    ("Funnel behavior issue", "View-to-cart or checkout-to-purchase drops for a category/device.", "Funnel tables show abandonment change by stage.", "Digital Analytics"),
    ("Service signal", "Contacts rise after fulfillment/inventory issue.", "Contact reasons correlate to affected orders/regions.", "Customer Service"),
    ("Finance caveat", "Net revenue differs from gross due to returns/tax/shipping.", "Finance daily table explains gross-to-net differences.", "Finance"),
]

DEMO_QUESTIONS = [
    "Why did digital conversion drop yesterday compared with the prior 7-day average?",
    "Which channels or campaigns contributed to the change?",
    "Did inventory availability contribute to the conversion decline?",
    "Did fulfillment delays or reduced fulfillment options contribute?",
    "Were customers abandoning in the checkout funnel?",
    "Did customer service contacts spike, and is it linked to the issue?",
    "Which vendor or category partner should we alert about stockouts?",
    "Why doesn't ecommerce sales match finance net revenue?",
    "What actions should marketing, merchandising, or operations investigate next?",
    "Show the retrieved definition and evidence path used for the answer.",
    "What caveats or data freshness limits should I know before trusting this result?",
]

# Functional requirements (id, requirement, priority, acceptance)
FUNC_REQS = [
    ("FR-01", "User can enter a performance question in Streamlit.", "Must", "Captured in session state and shown in debug trace."),
    ("FR-02", "Assistant detects ambiguous metric definitions.", "Must", "Clarifies or uses documented MVP default with caveat."),
    ("FR-03", "Assistant runs catalog sync/version checks.", "Must", "Stale ChromaDB chunks or graph versions refreshed/blocked."),
    ("FR-04", "Assistant retrieves top-k context from ChromaDB.", "Must", "Selected chunks appear in trust details with metadata."),
    ("FR-05", "Assistant validates retrieval against YAML.", "Must", "Unsupported definitions, tables, joins, filters rejected."),
    ("FR-06", "Assistant builds and traverses NetworkX graph.", "Must", "Returns campaign, inventory, fulfillment, owner paths."),
    ("FR-07", "Assistant activates ToT only for competing drivers.", "Must", "Trace shows ToT trigger decision and branch candidates."),
    ("FR-08", "Assistant validates SQL before execution.", "Must", "Only approved SELECT queries run."),
    ("FR-09", "Assistant executes DuckDB analysis over synthetic data.", "Must", "Evidence shows current, baseline, delta, % change, confidence."),
    ("FR-10", "Assistant applies evidence gate and stopping condition.", "Must", "Stops, retries once, or answers cautiously per rules."),
    ("FR-11", "Assistant creates evidence-backed final response.", "Must", "Includes definition, evidence, caveats, confidence, owners."),
    ("FR-12", "Assistant never writes to operational systems.", "Must", "Write requests refused and converted to recommendations."),
]

NON_FUNCTIONAL = [
    ("Local feasibility", "All MVP components run locally on a PC using free tools and synthetic data."),
    ("Transparency", "UI shows definition, chunks, graph path, SQL, evidence, branch scores, caveats."),
    ("Performance", "Query budget and beam width keep demo latency reasonable on local hardware."),
    ("Safety", "No PII, no proprietary data, no writes, no unsupported causality claims."),
    ("Repeatability", "Data generation and Chroma/graph rebuilds are repeatable with a fixed seed."),
    ("Maintainability", "YAML catalog is human-readable and small enough to inspect manually."),
]

# UI sections (section, content) - Plan section 17
UI_SECTIONS = [
    ("Business answer", "Plain-language result, ranked likely drivers, possible contributors, confidence."),
    ("Evidence", "Tables by channel/campaign, category/inventory, fulfillment, funnel; current/baseline/delta/% change/freshness."),
    ("Trust details", "Selected YAML definition, retrieved chunks, graph path, freshness, source versions, caveats, confidence."),
    ("ToT trace", "Candidate branches, scores, pruned branches, surviving branches, selection rationale."),
    ("SQL/Debug trace", "LangGraph nodes, tool outputs, SQL templates, query budget, validation results."),
    ("Action log", "Owner, issue, evidence, confidence, priority, recommended next step (human-reviewed only)."),
]

# Four trace levels (level, audience, content)
TRACE_LEVELS = [
    ("Level 1: Business summary", "Business users and leaders", "Final explanation, ranked drivers, confidence, caveats, owner actions."),
    ("Level 2: Evidence summary", "Analysts and managers", "Evidence tables, current vs baseline, contribution, freshness notes."),
    ("Level 3: Trust details", "Analysts, reviewers, stakeholder demo", "YAML definition, chunk titles, graph path, sync status, why ToT (not) triggered."),
    ("Level 4: Technical audit", "Developer / evaluator", "LangGraph node trace, tool-call summaries, SQL validation, branch scores, pruning, budget."),
]

# Audit event schema (field, example, purpose)
AUDIT_SCHEMA = [
    ("run_id", "2026-06-07-001", "Groups all events for one investigation."),
    ("event_id", "evt_006", "Stable ordering and traceability."),
    ("timestamp", "2026-06-07 14:32:11", "When each decision or tool call happened."),
    ("workflow_node", "retrieve_context, source_gate, tot_score", "Maps event to the LangGraph node."),
    ("decision_type", "metric_selected, branch_pruned, query_blocked", "The decision made."),
    ("tool_name", "ChromaDB, YAML parser, NetworkX, DuckDB", "Which tool was used."),
    ("input_summary", "metric=digital_conversion; baseline=prior_7_days", "Safe parameter summary."),
    ("output_summary", "Retrieved 5 chunks; selected certified definition", "Result of the step."),
    ("source_version_hash", "metrics.yaml v4 / hash match", "Chroma/graph synchronized with YAML."),
    ("score_or_confidence", "Branch score=10/14; confidence=medium", "Supports pruning/evidence gate."),
    ("status", "success, blocked, retried, caveated", "Whether the step passed or needed caution."),
    ("user_visible_note", "Inventory path checked; evidence weak -> inconclusive.", "Plain-language UI trace."),
]

# Implementation milestones (milestone, deliverables, exit)
MILESTONES = [
    ("1. Project setup", "Repository, environment, Streamlit shell, local model notes.", "App starts locally and accepts a question."),
    ("2. Synthetic data", "DuckDB schema, generator, seeded anomalies, validation SQL.", "Expected demo signals appear in data."),
    ("3. YAML catalog", "metrics, tables, drivers, rules, guardrails, examples, version manifest.", "Catalog parses, validates, produces content hashes."),
    ("4. Vector DB", "Chunk catalog/docs, embed, load ChromaDB, metadata checks.", "Search retrieves correct metric; stale chunks detected."),
    ("5. Knowledge graph", "NetworkX graph generated from YAML.", "Graph returns valid drivers, tables, owners, version metadata."),
    ("6. LangGraph workflow", "Classify, retrieve, validate, graph, ToT, SQL, evidence, synthesize nodes.", "Debug trace shows controlled reasoning loop."),
    ("7. ToT beam search", "Branch generator, scoring, pruning, tie-breaker, stopping rule.", "Demo shows candidate branches and selection."),
    ("8. Guardrails & evidence gate", "SQL validator, source gate, conflict checks, stopping, labels.", "Unsafe/unsupported answers blocked or caveated."),
    ("9. Demo polish", "Streamlit tabs, response template, action log, screenshots, assets.", "MVP is presentation-ready and repeatable."),
    ("10. Operations/finance backlog", "Service, funnel, finance, vendor, executive-summary placeholders.", "Future capabilities have a clear extension path."),
]

# Risks (risk, mitigation)
RISKS = [
    ("Scope becomes too broad.", "Keep MVP focused on conversion + campaign, inventory, fulfillment; defer service/finance depth."),
    ("Local model produces weak SQL.", "Approved templates, structured prompts, parameter filling, validation, fallbacks."),
    ("Vector retrieval returns stale/wrong definition.", "Validate vs YAML; metadata filters; reject version/hash mismatch."),
    ("NetworkX relationship incorrect or stale.", "Generate from YAML; test expected paths; block on version mismatch."),
    ("ToT branch explosion or latency.", "Trigger rule, beam width 2, depth limit 2, query budget, deterministic pruning."),
    ("Weak evaluation prunes the best branch.", "Combined rubric: source, graph, SQL, DuckDB evidence, freshness, actionability."),
    ("Synthetic data feels artificial.", "Seed realistic baselines, noise, multiple drivers; keep outcomes evaluation-only."),
    ("Prior memory biases the answer.", "Prior notes are context only; current DuckDB must confirm."),
    ("Answer overstates causality.", "Guarded language: likely driver, possible contributor, hypothesis, inconclusive."),
    ("Implementation looks more complex than MVP.", "CrewAI, MCP, Neo4j, cloud are future options, not MVP requirements."),
]

# Implementation-readiness checklist (question, answer)
READINESS = [
    ("Is every required component free for the MVP?", "Yes. Python, Streamlit, LangGraph, DuckDB, YAML, ChromaDB, sentence-transformers, NetworkX, Ollama, guardrails run locally."),
    ("Is Neo4j required?", "No. NetworkX suffices for the MVP. Neo4j is a future production option."),
    ("Is CrewAI required?", "No. Role separation uses LangGraph nodes and functions. CrewAI is optional."),
    ("Is MCP required?", "No. LangGraph state and local files are enough. MCP is a future option."),
    ("Does ToT require expensive compute?", "No. Bounded by trigger rules, beam width 2, depth limit 2, templates, query budget."),
    ("Can the synthetic data prove the demo?", "Yes. Seeded scenarios and validation SQL give repeatable patterns; outcomes are evaluation-only."),
    ("Can it answer safely without production access?", "Yes. Analyzes synthetic DuckDB data; human-reviewed recommendations only."),
    ("What prevents surprises?", "Version/hash sync, approved templates, deterministic validators, bounded budget, guarded language."),
]

# This prototype's status vs the plan (component, status, note)
PROTOTYPE_STATUS = [
    ("Faker synthetic data + seeded scenarios", "Built", "src/synthetic_data.py: fact_/dim_ model, 40+1 days, 5 scenarios, eval-only answer key."),
    ("Data validation (section 14.4)", "Built", "src/data_validation.py: all checks pass, drop in 15-25% band."),
    ("Split YAML catalog + version manifest", "Built", "catalog/*.yaml with per-file content hashes."),
    ("ChromaDB + sentence-transformers retrieval", "Built", "src/retrieval.py: real Chroma; ST->ONNX->hashing fallback; sync gate."),
    ("NetworkX graph from YAML", "Built", "src/graph.py: metric/table/system/driver/owner + edge types; version+hash gate."),
    ("LangGraph workflow", "Built", "src/workflow.py: real StateGraph, 10 nodes, ReAct loop."),
    ("Conditional ToT beam search", "Built", "src/tot.py: width 2, depth 2, rubric, pruning, budget, governance pre-screen."),
    ("Multi-agent team", "Built", "src/agents.py: specialized analysts, parallel dispatch, coordination log, graceful degradation; full team + executive summary."),
    ("Guardrails (SQL/freshness/conflict/write)", "Built", "src/guardrails.py driven by guardrails.yaml."),
    ("Audit trail + action log", "Built", "src/audit.py: run_id, section-17.2 event schema, human-reviewed actions."),
    ("Multi-tab UI + 4 trace levels", "Built", "app.py: Answer/Evidence/Trust/ToT/Audit/Action tabs."),
    ("Ollama LLM drafting", "Optional", "src/llm.py: used if a daemon is reachable; deterministic fallback otherwise."),
]
