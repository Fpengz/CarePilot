#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_ENV_FILE="$REPO_ROOT/apps/web/.env"

if [[ -f "$REPO_ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
  set +a
fi

# Optional web-only override layer. Values here take precedence over root .env.
if [[ -f "$WEB_ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$WEB_ENV_FILE"
  set +a
fi

exec "$@"
