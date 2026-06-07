"""
Structured content extracted from the project plan
("Omnichannel Retail Analytics Assistant - Updated Project Plan Through
Capstone Checkpoint 4.1"). Shared by the Streamlit app and the standalone
interactive HTML so both stay in sync with a single source.
"""

TITLE = "Omnichannel Retail Analytics Assistant"
SUBTITLE = "Updated Project Plan Through Capstone Checkpoint 4.1"

FEASIBILITY = (
    "This project is designed to be free and doable on a personal PC. The MVP "
    "uses local tools only: Python, Streamlit, LangGraph, DuckDB, YAML files, "
    "ChromaDB, sentence-transformers, NetworkX, Ollama, and custom guardrail "
    "functions. No paid cloud services, enterprise data, proprietary systems, "
    "production connectors, or production write access are required."
)

EXECUTIVE_SUMMARY = (
    "The assistant investigates omnichannel retail performance questions. Phase I "
    "focuses on the demo question: why did digital conversion drop yesterday "
    "compared with the prior 7-day average? It is not a general chatbot - it is a "
    "governed investigation workflow that retrieves definitions, validates source "
    "rules, traverses business relationships, explores competing hypotheses with "
    "bounded Tree-of-Thought reasoning when needed, runs read-only SQL over "
    "synthetic data, and produces evidence-backed recommendations with caveats and "
    "owner routing. The key Checkpoint 4.1 addition is a conditional Tree-of-Thought "
    "layer implemented as bounded beam search, activated only when multiple "
    "plausible driver paths compete."
)

BUSINESS_PROBLEM = (
    "Retail leaders ask simple questions whose answers span many systems. "
    "\"Why did digital conversion drop yesterday?\" may require website sessions, "
    "events, orders, inventory availability, fulfillment options, campaign mix, "
    "category behavior, service signals, finance caveats, and certified metric "
    "definitions. A prompt-only LLM is unreliable: it may use a generic conversion "
    "definition, ignore table grain, invent a root cause, or compare stale data. "
    "The assistant grounds each answer in governed context and query evidence "
    "before making a recommendation."
)

# (concept, demonstration, success measure)
CAPSTONE_FIT = [
    ("Tool calling",
     "Calls semantic search, YAML validation, graph traversal, SQL validation, DuckDB execution, profiling, ToT scoring, and action-log functions.",
     "Debug trace shows tools called in logical order with outputs used in the final answer."),
    ("Reasoning loop",
     "LangGraph coordinates a ReAct-style plan, act, observe, validate, revise, answer loop.",
     "Agent recovers from ambiguity, stale data, wrong grain, weak evidence, or source conflict."),
    ("Knowledge and memory",
     "ChromaDB retrieves catalog chunks, examples, SQL templates, caveats, and prior notes.",
     "Final answer shows selected definition and retrieved context summary."),
    ("Further reasoning / ToT",
     "Beam search explores competing driver hypotheses, scores branches, prunes weak paths, refines top candidates.",
     "System explains why it selected likely drivers and why other paths were pruned."),
    ("Multi-agent coordination",
     "Specialized agents evaluate marketing, merchandising, fulfillment, and later finance/service paths.",
     "At least one domain agent executes evidence analysis through validated tools."),
    ("Safety",
     "Read-only prototype on synthetic data. Guardrails block unsafe actions and unsupported claims.",
     "No write operations; weak causes are labeled as hypotheses or inconclusive."),
]

# (tool, role, free?, mvp notes)
TOOL_STACK = [
    ("Python", "Application runtime and data generation scripts", "Yes", "Local virtual environment."),
    ("Streamlit", "UI for questions, evidence, trust details, debug trace", "Yes", "Runs locally in browser."),
    ("LangGraph", "Orchestrates state machine, routing, query budget, stopping", "Yes", "Deterministic nodes for MVP."),
    ("Ollama", "Local LLM for planning and response drafting", "Yes", "Small local model; structured prompts."),
    ("YAML", "Governed source of truth for metrics, rules, caveats, guardrails", "Yes", "Plain text; inspectable, versionable."),
    ("ChromaDB", "Vector database for retrieval over YAML chunks and notes", "Yes", "Local persistent directory."),
    ("sentence-transformers", "Embedding model for local vector search", "Yes", "all-MiniLM-L6-v2 or similar."),
    ("NetworkX", "Local knowledge graph for metric-table-driver-owner", "Yes", "Python library; no server."),
    ("DuckDB", "Read-only analytics engine over synthetic tables", "Yes", "Local file database."),
    ("Guardrail functions", "SQL safety, freshness, conflict, evidence, ToT budget", "Yes", "Custom Python functions."),
    ("CrewAI / MCP", "Future role separation / shared-state option", "Optional", "Not a Phase I dependency."),
]

# Architecture layers (name, responsibility)
ARCH_LAYERS = [
    ("Streamlit UI", "Captures the question; renders evidence, trust details, and the debug trace."),
    ("LangGraph controller", "Central state machine: routing, query budget, and stopping decisions."),
    ("YAML catalog", "Authoritative source of truth. Every other layer is validated against it."),
    ("ChromaDB retrieval", "Semantic retrieval over YAML chunks, templates, examples, caveats, notes."),
    ("NetworkX graph", "Selects metric -> table -> driver -> owner relationships from the catalog."),
    ("Conditional ToT", "Bounded beam search over competing driver hypotheses (only when needed)."),
    ("DuckDB engine", "Produces read-only SQL evidence over synthetic retail tables."),
    ("Guardrails", "SQL safety, freshness, source-conflict, evidence-gate, budget, stopping checks."),
    ("Ollama LLM", "Helps with planning and summarization - never treated as a source of truth."),
]

# ToT scoring rubric (criterion, max score)
TOT_RUBRIC = [
    ("Metric definition validated against YAML", 2),
    ("Approved graph path exists", 2),
    ("SQL passes validator", 2),
    ("DuckDB result shows meaningful delta or contribution", 3),
    ("Freshness and row quality acceptable", 2),
    ("Business relevance and owner actionability", 2),
    ("Caveats manageable", 1),
]
TOT_THRESHOLDS = (
    "Branches scoring below 7 are pruned. Scores 7-9 are possible contributors. "
    "Scores 10+ may be ranked as likely drivers if evidence is consistent. Ties "
    "are resolved by stronger DuckDB evidence, fewer caveats, and clearer owner "
    "actionability. If all branches fail, the assistant answers inconclusive and "
    "recommends next checks."
)

# Source-conflict priority rules (situation, decision, user-facing behavior)
CONFLICT_RULES = [
    ("ChromaDB definition conflicts with YAML", "YAML wins (governed truth).", "States certified definition or asks clarification."),
    ("NetworkX relationship conflicts with YAML", "YAML wins; graph regenerated/flagged.", "Avoids disputed path or discloses uncertainty."),
    ("Retrieved example suggests unsupported table", "SQL validator blocks unless YAML-approved.", "Revises plan before querying."),
    ("DuckDB evidence does not support hypothesis", "DuckDB evidence controls the claim.", "Labels hypothesis inconclusive."),
    ("Multiple valid definitions exist", "Ask clarification or use documented default.", "Explains which definition is used."),
]

# Seeded synthetic scenarios (scenario, injected pattern, expected evidence, owner)
SCENARIOS = [
    ("Digital conversion drop", "Yesterday conversion declines 15-25% vs prior 7-day average.", "Overall delta and contribution ranking show the drop.", "Analytics / Leadership"),
    ("Paid social traffic shift", "Paid social sessions spike but convert below baseline.", "Channel tables show higher traffic share, lower conversion.", "Marketing"),
    ("Inventory availability issue", "Selected categories: high product views, low available-online.", "High traffic, low conversion, elevated stockout rate.", "Merchandising"),
    ("Fulfillment constraint", "Delivery delays or fewer options in selected regions.", "Higher delay_days, cancellations, lower option availability.", "Fulfillment Operations"),
    ("Service signal (Phase II)", "Contacts rise after fulfillment/inventory issue.", "Contact reasons correlate to affected orders/regions.", "Customer Service"),
    ("Finance caveat (Phase III)", "Net revenue differs from gross due to returns/tax/shipping.", "Finance table explains gross-to-net differences.", "Finance"),
]

DEMO_QUESTIONS = [
    "Why did digital conversion drop yesterday compared with the prior 7-day average?",
    "Which channels or campaigns contributed to the change?",
    "Did inventory availability contribute to the conversion decline?",
    "Did fulfillment delays or reduced fulfillment options contribute?",
    "What actions should marketing, merchandising, or operations investigate next?",
    "Show the retrieved definition and evidence path used for the answer.",
    "What caveats or data freshness limits should I know before trusting this result?",
]

# Functional requirements (id, requirement, acceptance criteria)
FUNC_REQS = [
    ("FR-01", "User can enter a performance question in Streamlit.", "Question captured in session state and shown in debug trace."),
    ("FR-02", "Retrieve top-k governed context and validate against YAML.", "Answer includes selected definition, caveats, retrieval summary."),
    ("FR-03", "Check ChromaDB and NetworkX freshness against YAML.", "Stale chunks/graph versions are refreshed or blocked."),
    ("FR-04", "Use conditional ToT beam search for competing drivers.", "Trace shows candidate branches, scores, pruned paths, selected beam."),
    ("FR-05", "Validate SQL before execution.", "Only approved SELECT queries run."),
    ("FR-06", "Execute DuckDB analysis over synthetic data.", "Evidence shows current, baseline, delta, % change, confidence."),
    ("FR-07", "Apply evidence gate and stopping condition.", "Stops, retries once, or answers cautiously per rules."),
    ("FR-08", "Create final grounded response.", "Includes definition, evidence, caveats, confidence, action owners."),
    ("FR-09", "Never write to operational systems.", "Write requests refused and converted to recommendations."),
]

# Implementation milestones (phase, deliverables, exit criteria)
MILESTONES = [
    ("1. Project setup", "Repo, environment, Streamlit shell, local model notes.", "App starts locally and accepts a question."),
    ("2. Synthetic data", "DuckDB schema, generator, seeded anomalies, validation SQL.", "Expected demo signals appear in data."),
    ("3. YAML catalog", "Metrics, tables, drivers, rules, guardrails, examples.", "Catalog parses and validates."),
    ("4. Vector DB", "Chunk catalog/docs, embed, load ChromaDB, add content hashes.", "Search retrieves correct metric and rejects stale chunks."),
    ("5. Knowledge graph", "NetworkX graph from YAML with catalog_version.", "Graph returns valid drivers/tables/owners; stale graph blocked."),
    ("6. LangGraph workflow", "Classify, retrieve, validate, graph, ToT, plan, query, synthesize nodes.", "Debug trace shows controlled reasoning loop."),
    ("7. ToT + evidence gate", "Beam search, scoring rubric, pruning thresholds, stopping.", "Trace shows branches scored and pruned within budget."),
    ("8. Demo polish", "Response templates, action log, screenshots, report assets.", "MVP is presentation-ready."),
]

# Risks (risk, mitigation)
RISKS = [
    ("Scope becomes too broad", "Keep MVP focused on conversion + campaign, inventory, fulfillment drivers."),
    ("ToT branch explosion", "Trigger rule, beam width 2, depth limit 2, fixed query budget."),
    ("Weak evaluation prunes best branch", "Deterministic scorecard + DuckDB evidence + one targeted follow-up."),
    ("Local model produces weak SQL", "Structured prompts, approved templates, validation, fallbacks."),
    ("Vector retrieval returns stale definition", "Validate against YAML; check version/content_hash."),
    ("Graph relationship stale/incorrect", "Generate from YAML, store catalog_version, test expected paths."),
    ("Synthetic data feels artificial", "Seed realistic scenarios with baselines, noise, evaluation-only outcomes."),
    ("Answer overstates causality", "Use likely-driver / possible-contributor / hypothesis / inconclusive labels."),
]

# Implementation status of THIS prototype against the plan (item, status, note)
PROTOTYPE_STATUS = [
    ("Streamlit UI + debug trace", "Built", "This app: question box, evidence, trust panel, trace."),
    ("Synthetic data + seeded anomalies", "Built", "src/synthetic_data.py - 4 scenarios, fixed seed."),
    ("YAML governed catalog", "Built", "catalog/catalog.yaml with version + content_hash."),
    ("NetworkX graph from YAML", "Built", "src/graph.py - version-stamped, freshness-gated."),
    ("Read-only DuckDB evidence", "Built", "src/investigation.py runs live SELECT queries."),
    ("Conditional ToT beam search", "Built", "Width 2, depth 2, scoring rubric, pruning, budget."),
    ("Guardrails (SQL/freshness/write)", "Built", "src/guardrails.py - validator + write refusal."),
    ("ChromaDB vector retrieval", "Stubbed", "Chunking modeled in catalog.chunks(); embeddings optional."),
    ("Ollama LLM planning/drafting", "Optional", "Deterministic stand-in; LLM not required to run demo."),
    ("LangGraph orchestration", "Modeled", "Deterministic pipeline mirrors the planned node graph."),
]
