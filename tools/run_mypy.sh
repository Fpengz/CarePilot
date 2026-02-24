#!/usr/bin/env bash
set -euo pipefail
# Run mypy from inside src to avoid duplicate-module mapping issues
cd "$(dirname "$0")/.." || exit 1
cd src
../.venv/bin/python -m mypy --strict dietary_guardian
