# CLAUDE.md

See [AGENTS.md](AGENTS.md) for project-wide rules and the agent roster.

Quick reminders:
- Run with `python tools.py run`; verify with `python -m src.data_validation` and the
  `AppTest` smoke checks (keep page renders at 0 exceptions) before committing.
- Read-only, governed, free/local stack. YAML catalog is the source of truth; no writes
  to operational systems; label causality, never assert it.
- Specialized analyst definitions live in [`agents/`](agents/).
