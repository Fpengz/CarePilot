#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

API_LOG="${TMPDIR:-/tmp}/dg_api_postgres_redis.log"
WORKER_LOG="${TMPDIR:-/tmp}/dg_worker_postgres_redis.log"
COOKIE_JAR="${TMPDIR:-/tmp}/dg_smoke_cookies.txt"
API_PID=""
WORKER_PID=""

cleanup() {
  local code="${1:-0}"
  trap - EXIT INT TERM
  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "$WORKER_PID" ]] && kill -0 "$WORKER_PID" >/dev/null 2>&1; then
    kill "$WORKER_PID" >/dev/null 2>&1 || true
  fi
  wait >/dev/null 2>&1 || true
  exit "$code"
}

trap 'cleanup 130' INT TERM
trap 'cleanup $?' EXIT

export LLM_PROVIDER="${LLM_PROVIDER:-test}"
export APP_DATA_BACKEND="${APP_DATA_BACKEND:-postgres}"
export AUTH_STORE_BACKEND="${AUTH_STORE_BACKEND:-postgres}"
export HOUSEHOLD_STORE_BACKEND="${HOUSEHOLD_STORE_BACKEND:-postgres}"
export EPHEMERAL_STATE_BACKEND="${EPHEMERAL_STATE_BACKEND:-redis}"
export POSTGRES_DSN="${POSTGRES_DSN:-postgresql://dietary_guardian:dietary_guardian@127.0.0.1:5432/dietary_guardian}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
export REDIS_WORKER_SIGNAL_CHANNEL="${REDIS_WORKER_SIGNAL_CHANNEL:-workers.ready}"
export API_HOST="${API_HOST:-127.0.0.1}"
export API_PORT="${API_PORT:-8001}"
export WORKER_MODE="${WORKER_MODE:-external}"

command -v curl >/dev/null 2>&1 || { echo "Missing dependency: curl" >&2; exit 1; }
command -v uv >/dev/null 2>&1 || { echo "Missing dependency: uv" >&2; exit 1; }

./scripts/dev-infra.sh up
./scripts/migrate-postgres.sh

rm -f "$COOKIE_JAR"

echo "[smoke] starting API (logs: $API_LOG)"
uv run python -m apps.api.run >"$API_LOG" 2>&1 &
API_PID=$!

echo "[smoke] starting worker (logs: $WORKER_LOG)"
uv run python -m apps.workers.run >"$WORKER_LOG" 2>&1 &
WORKER_PID=$!

for _ in $(seq 1 40); do
  if curl -sf "http://${API_HOST}:${API_PORT}/api/v1/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

curl -sf "http://${API_HOST}:${API_PORT}/api/v1/health/ready" >/dev/null

LOGIN_RESPONSE="$(
  curl -sf -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
    -H "Content-Type: application/json" \
    -d '{"email":"member@example.com","password":"member-pass"}' \
    "http://${API_HOST}:${API_PORT}/api/v1/auth/login"
)"
echo "$LOGIN_RESPONSE" | uv run --no-project python - <<'PY' >/dev/null
import json
import sys
payload = json.load(sys.stdin)
assert payload["user"]["email"] == "member@example.com"
PY

GENERATE_RESPONSE="$(
  curl -sf -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
    -X POST "http://${API_HOST}:${API_PORT}/api/v1/reminders/generate"
)"

REMINDER_ID="$(echo "$GENERATE_RESPONSE" | uv run --no-project python - <<'PY'
import json
import sys
payload = json.load(sys.stdin)
items = payload.get("reminders") or []
if not items:
    raise SystemExit("no reminders generated")
print(items[0]["id"])
PY
)"

DELIVERED=0
for _ in $(seq 1 25); do
  SCHEDULES="$(
    curl -sf -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
      "http://${API_HOST}:${API_PORT}/api/v1/reminders/${REMINDER_ID}/notification-schedules"
  )"
  if echo "$SCHEDULES" | uv run --no-project python - <<'PY' >/dev/null
import json
import sys
payload = json.load(sys.stdin)
items = payload.get("items") or []
if not items:
    raise SystemExit(1)
statuses = {item.get("status") for item in items}
if "delivered" in statuses:
    raise SystemExit(0)
raise SystemExit(1)
PY
  then
    DELIVERED=1
    break
  fi
  sleep 1
done

if [[ "$DELIVERED" -ne 1 ]]; then
  echo "[smoke] notification schedules did not reach delivered state in time." >&2
  echo "[smoke] API log tail:" >&2
  tail -n 80 "$API_LOG" >&2 || true
  echo "[smoke] Worker log tail:" >&2
  tail -n 80 "$WORKER_LOG" >&2 || true
  exit 1
fi

echo "[smoke] success: postgres+redis API and worker flow is healthy."
echo "[smoke] API log: $API_LOG"
echo "[smoke] Worker log: $WORKER_LOG"
