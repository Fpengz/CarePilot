#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORTS_DIR="$ROOT_DIR/reports"
TEMPLATE="$REPORTS_DIR/nightly_TEMPLATE.md"
DATE_STAMP="${1:-$(date +%F)}"
REPORT_PATH="$REPORTS_DIR/nightly_${DATE_STAMP}.md"

mkdir -p "$REPORTS_DIR"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "Missing template: $TEMPLATE" >&2
  exit 1
fi

if [[ -f "$REPORT_PATH" ]]; then
  echo "$REPORT_PATH"
  exit 0
fi

cp "$TEMPLATE" "$REPORT_PATH"

echo "$REPORT_PATH"
