# CarePilot

CarePilot is an AI health companion for chronic-condition support outside the clinic. It combines meal analysis, reminders, adherence tracking, symptoms, reports, clinician-facing digests, and impact tracking in a modular-monolith architecture.

## What the System Does
- Builds a longitudinal patient view from meals, reminders, adherence events, symptoms, biomarkers, and profile context.
- Personalizes companion guidance for `chat`, `meal_review`, `check_in`, `report_follow_up`, and `adherence_follow_up`.
- Runs deterministic evidence and safety checks before returning care guidance.
- Generates clinician digests and impact summaries from the same underlying case state.
- Supports Singapore-local meal reasoning with deterministic canonical-food normalization.

## Current Status (Phase 4 Active)
- **Phase 3 Complete**: All API schemas moved to `src/care_pilot/core/contracts/api/`. Cross-feature orchestration moved to the API layer. Circular imports resolved.
- **Companion Spine**: `features/companion/**` is the product spine, coordinating chat, recommendations, and emotion.
- **Workflows**: Multi-step journeys for meals and medications are managed via `pydantic-graph`.
- **Inference**: Agents are bounded, inference-only components using `pydantic_ai`.

## Repository Shape

```text
apps/
  api/        FastAPI transport layer (transport-only routers)
  web/        Next.js frontend (Next.js 14 App Router)
  workers/    Async worker runtime (reminders, outbox)
src/
  care_pilot/
    core/            Shared primitives and canonical API contracts
    features/        Product behavior, use-cases, and domain logic
    agent/           Bounded inference-only agents
    platform/        Infrastructure adapters (persistence, auth, messaging)
docs/         Canonical documentation and refactor history
tests/        Repository-level tests and meta-guardrails
```

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

## Canonical Documentation
- `ARCHITECTURE.md`: Detailed system architecture, boundaries, and rules.
- `docs/refactor_plan.md`: Refactor history, phases, and active naming cleanup.
- `SYSTEM_ROADMAP.md`: Current status, delivered capabilities, and next phases.
- `CONTRIBUTING.md`: Contributor workflow and review expectations.
- `docs/README.md`: Index of focused references.
