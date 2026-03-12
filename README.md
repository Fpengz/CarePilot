# Dietary Guardian SG

Dietary Guardian SG is an AI health companion for chronic-condition support outside the clinic. It combines meal analysis, reminders, adherence tracking, symptoms, reports, clinician-facing digests, and impact tracking in a modular-monolith architecture.

## What the system does
- builds a longitudinal patient view from meals, reminders, adherence events, symptoms, biomarkers, and profile context
- personalizes companion guidance for `chat`, `meal_review`, `check_in`, `report_follow_up`, and `adherence_follow_up`
- runs deterministic evidence and safety checks before returning care guidance
- generates clinician digests and impact summaries from the same underlying case state
- supports Singapore-local meal reasoning with deterministic canonical-food normalization

## Companion chat + dashboard (refactored)
- streaming chat with audio transcription and emotion context injection
- `[TRACK]` parsing with health-metric chart data and trend computation
- RAG routing for drug/food/general queries and local Singapore food retrieval
- E2B sandboxed calculations for dashboard trends
Endpoint surface:
- `/api/v1/chat` + `/api/v1/chat/audio` + `/api/v1/chat/history`
- `/api/v1/dashboard/entries` + `/api/v1/dashboard/chart-data` + `/api/v1/dashboard/trend`

## Repository shape

```text
apps/
  api/        FastAPI transport layer
  web/        Next.js frontend
  workers/    async worker runtime
src/
  dietary_guardian/
    core/            tiny shared primitives and base contracts
    features/        product behavior and service entrypoints
    agent/           bounded model/provider logic
    platform/        persistence, auth, scheduling, storage, observability
    shared/          shared utilities (time, etc.)
docs/         canonical docs and focused references
tests/        repository-level tests
```

## Architecture in one view
- `apps/web` is the main patient and admin interface
- `apps/api` keeps routers thin and maps HTTP requests into feature services
- `src/dietary_guardian/features` owns companion logic such as case snapshots, personalization, engagement, care plans, clinician digests, impact, and safety
- `src/dietary_guardian/platform` owns persistence and external integrations
- `apps/workers` runs reminder, outbox, and related async processing
- `src/dietary_guardian/agent` stays bounded behind typed inputs and outputs; deterministic logic remains the source of truth for durable health state
- chat-specific agents live under `src/dietary_guardian/agent/chat/`

## Quickstart

Requirements:
- Python 3.12+
- Node.js 20+
- `uv`
- `pnpm`

Install:

```bash
uv sync
pnpm install
cp .env.example .env
```

Run the default local stack:

```bash
uv run python scripts/cli.py dev
```

Useful variants:

```bash
uv run python scripts/cli.py dev --no-web
uv run python scripts/cli.py dev --no-api
uv run python scripts/cli.py dev --no-scheduler
```

Hackathon local stack:

```bash
uv run python scripts/cli.py infra up
```

## Validation

Backend:

```bash
uv run ruff check .
uv run ty check . --extra-search-path src --output-format concise
uv run pytest -q
```

Web:

```bash
pnpm web:lint
pnpm web:typecheck
pnpm web:build
```

Full stack:

```bash
uv run python scripts/cli.py test comprehensive

Ingestion:
- ChromaDB hawker/drinks: `uv run python scripts/cli.py ingest local`
- USDA JSON → SQLite: `uv run python scripts/cli.py ingest usda <path> [--reset]`
- Open Food Facts JSON → SQLite: `uv run python scripts/cli.py ingest off <path> [--reset]`
```

## Canonical documentation
- `ARCHITECTURE.md`: system architecture, boundaries, and runtime model
- `SYSTEM_ROADMAP.md`: current status, delivered capabilities, and next phases
- `CONTRIBUTING.md`: contributor workflow, branch/merge rules, validation, and review expectations
- `docs/README.md`: index of the remaining focused docs
- `docs/developer-guide.md`: local development and extension patterns
- `docs/operations-runbook.md`: runtime operations and incident workflow
- `docs/user-manual.md`: end-user and admin/operator flows
