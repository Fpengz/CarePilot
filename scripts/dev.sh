#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Export project root .env values for both API and Web dev processes.
if [[ -f "$REPO_ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
  set +a
fi

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

detect_lan_ip() {
  local ip=""
  if command -v ipconfig >/dev/null 2>&1; then
    ip="$(ipconfig getifaddr en0 2>/dev/null || true)"
    if [[ -z "$ip" ]]; then
      ip="$(ipconfig getifaddr en1 2>/dev/null || true)"
    fi
  fi
  if [[ -z "$ip" ]] && command -v ifconfig >/dev/null 2>&1; then
    ip="$(ifconfig | awk '/inet / && $2 !~ /^127\\./ { print $2; exit }')"
  fi
  printf "%s" "$ip"
}

LAN_IP="$(detect_lan_ip)"
LAN_ORIGIN=""
if [[ -n "$LAN_IP" ]]; then
  LAN_ORIGIN="http://${LAN_IP}:3000"
fi

DEFAULT_API_CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
DEFAULT_NEXT_ALLOWED_DEV_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
if [[ -n "$LAN_ORIGIN" ]]; then
  DEFAULT_API_CORS_ORIGINS="${DEFAULT_API_CORS_ORIGINS},${LAN_ORIGIN}"
  DEFAULT_NEXT_ALLOWED_DEV_ORIGINS="${DEFAULT_NEXT_ALLOWED_DEV_ORIGINS},${LAN_ORIGIN}"
fi

export API_CORS_ORIGINS="${API_CORS_ORIGINS:-$DEFAULT_API_CORS_ORIGINS}"
export NEXT_ALLOWED_DEV_ORIGINS="${NEXT_ALLOWED_DEV_ORIGINS:-$DEFAULT_NEXT_ALLOWED_DEV_ORIGINS}"
export NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-/backend}"
export BACKEND_API_BASE_URL="${BACKEND_API_BASE_URL:-http://127.0.0.1:8001}"
export NEXT_PUBLIC_MEAL_ANALYZE_PROVIDER="${NEXT_PUBLIC_MEAL_ANALYZE_PROVIDER:-${LLM_PROVIDER:-test}}"
export API_DEV_LOG_VERBOSE="${API_DEV_LOG_VERBOSE:-1}"
export API_DEV_LOG_HEADERS="${API_DEV_LOG_HEADERS:-0}"
export API_DEV_LOG_RESPONSE_HEADERS="${API_DEV_LOG_RESPONSE_HEADERS:-0}"
export NEXT_PUBLIC_DEV_LOG_FRONTEND="${NEXT_PUBLIC_DEV_LOG_FRONTEND:-1}"
export NEXT_PUBLIC_DEV_LOG_FRONTEND_VERBOSE="${NEXT_PUBLIC_DEV_LOG_FRONTEND_VERBOSE:-0}"

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
echo "[dev] API_CORS_ORIGINS=$API_CORS_ORIGINS"
echo "[dev] NEXT_ALLOWED_DEV_ORIGINS=$NEXT_ALLOWED_DEV_ORIGINS"
echo "[dev] NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL"
echo "[dev] BACKEND_API_BASE_URL=$BACKEND_API_BASE_URL"
echo "[dev] NEXT_PUBLIC_MEAL_ANALYZE_PROVIDER=$NEXT_PUBLIC_MEAL_ANALYZE_PROVIDER"
if [[ -f "$REPO_ROOT/apps/web/.env" ]]; then
  echo "[dev] apps/web/.env override detected (applies to web:* scripts)"
else
  echo "[dev] apps/web/.env override not set"
fi
echo "[dev] API_DEV_LOG_VERBOSE=$API_DEV_LOG_VERBOSE API_DEV_LOG_HEADERS=$API_DEV_LOG_HEADERS API_DEV_LOG_RESPONSE_HEADERS=$API_DEV_LOG_RESPONSE_HEADERS"
echo "[dev] NEXT_PUBLIC_DEV_LOG_FRONTEND=$NEXT_PUBLIC_DEV_LOG_FRONTEND NEXT_PUBLIC_DEV_LOG_FRONTEND_VERBOSE=$NEXT_PUBLIC_DEV_LOG_FRONTEND_VERBOSE"
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
