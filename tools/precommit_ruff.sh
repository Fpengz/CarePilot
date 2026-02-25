#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
uv run ruff check .
