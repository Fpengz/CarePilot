#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.." || exit 1

timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

log() {
  printf '[%s] %s\n' "$(timestamp)" "$*"
}

usage() {
  cat <<'EOF'
Usage: ./tools/validate.sh <preset>

Presets:
  backend-milestone   Targeted backend milestone checks (sqlite auth + household slices)
  backend-all         Repo backend checks (ruff, ty, pytest)
  full-stack          Backend checks + web typecheck/build
EOF
}

run_backend_milestone() {
  log "Running targeted backend milestone checks"
  log "pytest: auth + sqlite auth + households"
  uv run pytest \
    apps/api/tests/test_api_households.py \
    apps/api/tests/test_api_auth.py \
    apps/api/tests/test_api_auth_sqlite_backend.py \
    tests/test_sqlite_auth_store.py \
    apps/api/tests/test_auth_store.py \
    -q

  log "ty: focused API/household modules"
  uv run ty check \
    apps/api/dietary_api \
    src/dietary_guardian/application/household \
    src/dietary_guardian/infrastructure/household \
    src/dietary_guardian/infrastructure/auth \
    --output-format concise
}

run_backend_all() {
  log "Running backend-all checks"
  uv run ruff check .
  uv run ty check . --extra-search-path src --output-format concise
  uv run pytest -q
}

run_full_stack() {
  log "Running full-stack checks"
  run_backend_all
  pnpm web:typecheck
  pnpm web:build
}

if [[ $# -ne 1 ]]; then
  usage >&2
  exit 2
fi

case "$1" in
  backend-milestone)
    run_backend_milestone
    ;;
  backend-all)
    run_backend_all
    ;;
  full-stack)
    run_full_stack
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Unknown preset: $1" >&2
    usage >&2
    exit 2
    ;;
esac

log "Validation preset '$1' completed successfully"
