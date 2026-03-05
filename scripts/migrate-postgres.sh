#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_POSTGRES_DSN="postgresql://dietary_guardian:dietary_guardian@127.0.0.1:5432/dietary_guardian"

cd "$ROOT_DIR"

POSTGRES_DSN="${POSTGRES_DSN:-$DEFAULT_POSTGRES_DSN}"
export POSTGRES_DSN

uv run python -m dietary_guardian.infrastructure.persistence.postgres_schema "${POSTGRES_DSN}"
