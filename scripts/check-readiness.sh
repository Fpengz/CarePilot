#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8001}"
STRICT_WARNINGS="${READINESS_FAIL_ON_WARNINGS:-0}"
READY_URL="${BASE_URL%/}/api/v1/health/ready"

command -v curl >/dev/null 2>&1 || { echo "Missing dependency: curl" >&2; exit 127; }
command -v uv >/dev/null 2>&1 || { echo "Missing dependency: uv" >&2; exit 127; }

PAYLOAD="$(curl -sf "$READY_URL")"

STATUS="$(
  uv run --no-project python -c 'import json,sys; body=json.load(sys.stdin); print(body.get("status","unknown"))' <<<"$PAYLOAD"
)"

uv run --no-project python -c '
import json
import sys
body = json.load(sys.stdin)
print(f"readiness.status={body.get(\"status\")}")
print(f"readiness.warnings={len(body.get(\"warnings\") or [])}")
print(f"readiness.errors={len(body.get(\"errors\") or [])}")
for warning in body.get("warnings") or []:
    print(f"warning: {warning}")
for error in body.get("errors") or []:
    print(f"error: {error}")
' <<<"$PAYLOAD"

if [[ "$STATUS" == "not_ready" ]]; then
  exit 1
fi

if [[ "$STATUS" == "degraded" && "$STRICT_WARNINGS" == "1" ]]; then
  exit 1
fi

exit 0
