#!/bin/bash
# SessionStart hook for Claude Code on the web.
# Installs the free/local dependencies and pre-warms the local ChromaDB vector
# index so the first Live Demo run is fast. Synchronous (the session waits until
# this completes) - this guarantees deps are ready before any test/lint/app run.
set -euo pipefail

# Only run in the remote (Claude Code on the web) environment.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

echo "[session-start] Installing Python dependencies (free/local stack)…"
# --ignore-installed PyYAML avoids a collision with the system (Debian) PyYAML
# that otherwise blocks the chromadb install.
python3 -m pip install --quiet --ignore-installed PyYAML -r requirements.txt

echo "[session-start] Validating synthetic data pipeline…"
python3 -m evals.validation >/dev/null

echo "[session-start] Pre-warming ChromaDB vector index (downloads embedding model once)…"
# Non-fatal: if the embedding model can't be fetched, retrieval falls back to a
# deterministic hashing embedder at runtime, so the session should not block.
python3 -c "from skills.retrieval_skill import get_index; print('embedder:', get_index().embedder_label)" || \
  echo "[session-start] index pre-warm skipped (will fall back at runtime)"

echo "[session-start] Done."
