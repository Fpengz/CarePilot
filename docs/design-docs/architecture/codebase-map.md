# Codebase Map

> **Status**: Current (updated March 29, 2026)
> **Scope**: Feature-first modular monolith with thin `apps/` entrypoints.

## Top-Level Layout

```text
apps/
  api/          FastAPI transport layer
  inference/    inference runtime service
  web/          Next.js 14 UI
  workers/      async worker runtime
src/
  care_pilot/
    core/       tiny shared primitives
    features/   product behavior and service entrypoints
    agent/      bounded model/provider logic
    platform/   persistence + integrations
    config/     settings composition root
    shared/     shared utilities (time, etc.)
docs/           system-of-record knowledge base (design docs, plans, specs, references)
tests/          unit/integration/e2e
```

## Key Entrypoints

- **API app**: `apps/api/carepilot_api/main.py`
- **API routing**: `apps/api/carepilot_api/routers/`
- **API deps/context**: `apps/api/carepilot_api/deps.py`
- **API policy**: `apps/api/carepilot_api/policy.py`
- **Inference runtime**: `apps/inference/run.py`
- **Web app**: `apps/web/app/`
- **Workers**: `apps/workers/run.py`

## Feature Layer (Product Behavior)

Location: `src/care_pilot/features/`

Key modules:
- **companion/**: core care-loop modules
  - `core/` (case snapshot + evidence/health state)
  - `personalization/`, `engagement/`, `care_plans/`
  - `clinician_digest/`, `impact/`, `interactions/`
- **meals/**: meal analysis + records
- **recommendations/**: daily suggestions + substitutions
- **reminders/**: reminders + notifications
- **medications/**: regimens + adherence
- **reports/**: biomarker parsing + reports
- **symptoms/**, **profiles/**, **households/**, **safety/**

Feature entrypoints are typically `service.py` or `use_cases.py` under each feature.

## Agent Layer (Bounded AI)

Location: `src/care_pilot/agent/`

Modules:
- **core/**: base agent contracts and registry
- **runtime/**: inference engine, routing, model factory/types
- **chat/**: companion chat pipeline
- **meal_analysis/**: meal perception pipeline
- **dietary/**: dietary claims extraction
- **emotion/**: canonical emotion inference runtime
- **recommendation/**: recommendation agent

Agents do not own durable state; they enrich or propose.

## Platform Layer (Infrastructure)

Location: `src/care_pilot/platform/`

Key areas:
- **persistence/**: SQLModel + SQLite repositories and migrations
- **auth/**: sessions + signers
- **cache/**: in-memory/redis stores
- **messaging/**: notification channels
- **scheduling/**: worker coordination
- **storage/**: media upload/ingestion
- **observability/**: logging + tooling + workflows

## Data & Runtime Artifacts

- **Static datasets**: `src/care_pilot/data/`
- **Runtime**: `data/runtime/` and `data/vectorstore/` (git-ignored)

## Extension Pointers

- Add new product behavior under `features/<feature>/service.py`.
- Add new model/runtime logic under `agent/<agent>/`.
- Add new infra integration under `platform/<area>/`.
- Keep routers thin: map requests to feature services.
