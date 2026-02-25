#!/usr/bin/env bash
set -euo pipefail

# Run quality gates from repository root.
cd "$(dirname "$0")/.." || exit 1

timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

log() {
  printf '[%s] %s\n' "$(timestamp)" "$*"
}

trap 'log "FAILED at line $LINENO"' ERR

log "Starting quality gate checks"
log "Running: ruff"
uv run ruff check .

log "Running: ty"
uv run ty check . --extra-search-path src --output-format concise

log "Running: pytest"
uv run pytest -q

log "Completed quality gate checks successfully"
