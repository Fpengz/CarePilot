#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

START_API=1
START_WEB=1

usage() {
  cat <<'EOF'
Usage: ./scripts/dev.sh [--no-api] [--no-web] [--help]

Starts local development services:
- FastAPI API on http://localhost:8001
- Next.js web app on http://localhost:3000

Options:
  --no-api   Start only the web app
  --no-web   Start only the API
  --help     Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-api)
      START_API=0
      shift
      ;;
    --no-web)
      START_WEB=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$START_API" -eq 0 && "$START_WEB" -eq 0 ]]; then
  echo "Nothing to start: both --no-api and --no-web were set." >&2
  exit 2
fi

command -v uv >/dev/null 2>&1 || { echo "Missing dependency: uv" >&2; exit 1; }
command -v pnpm >/dev/null 2>&1 || { echo "Missing dependency: pnpm" >&2; exit 1; }

API_PID=""
WEB_PID=""

cleanup() {
  local exit_code=${1:-0}
  trap - INT TERM EXIT
  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "$WEB_PID" ]] && kill -0 "$WEB_PID" >/dev/null 2>&1; then
    kill "$WEB_PID" >/dev/null 2>&1 || true
  fi
  wait >/dev/null 2>&1 || true
  exit "$exit_code"
}

trap 'cleanup 130' INT TERM
trap 'cleanup $?' EXIT

if [[ "$START_API" -eq 1 ]]; then
  echo "[dev] starting API: uv run python -m apps.api.run"
  uv run python -m apps.api.run &
  API_PID=$!
fi

if [[ "$START_WEB" -eq 1 ]]; then
  echo "[dev] starting Web: pnpm web:dev"
  pnpm web:dev &
  WEB_PID=$!
fi

if [[ -n "$API_PID" ]]; then
  echo "[dev] API PID: $API_PID (http://localhost:8001)"
fi
if [[ -n "$WEB_PID" ]]; then
  echo "[dev] Web PID: $WEB_PID (http://localhost:3000)"
fi
echo "[dev] Press Ctrl+C to stop."

while :; do
  if [[ -n "$API_PID" ]] && ! kill -0 "$API_PID" >/dev/null 2>&1; then
    wait "$API_PID"
    echo "[dev] API exited; stopping remaining services." >&2
    exit 1
  fi
  if [[ -n "$WEB_PID" ]] && ! kill -0 "$WEB_PID" >/dev/null 2>&1; then
    wait "$WEB_PID"
    echo "[dev] Web exited; stopping remaining services." >&2
    exit 1
  fi
  sleep 1
done
