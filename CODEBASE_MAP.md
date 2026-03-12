# Codebase Map: dietary_tools

> **Status**: Current (updated March 12, 2026)  
> **Scope**: Feature-first modular monolith with thin apps/ entrypoints.

## 0. Merge Provenance (Ervin + Xiangqi)

This codebase is the result of merging two Healthcare-Agent branches into the
feature-first architecture:

- **ervin branch (`healthcare/ervin`)**
  - Chat pipeline refactored into `src/dietary_guardian/agent/chat/`
  - API entrypoints: `apps/api/dietary_api/routers/chat.py` and `dashboard.py`
  - Web entrypoint: `apps/web/app/chat/`
  - Food local retrieval ingester/retriever under `platform/persistence/food/`

- **xiangqi branch (`healthcare/xiangqi`)**
  - Hybrid food retrieval (vector + keyword rerank) refactored into
    `src/dietary_guardian/platform/persistence/food/hybrid_search.py`
  - Runtime artifacts (vectorstore/db) intentionally removed; they are now
    expected under `data/vectorstore/` at runtime only

## 1. Top-Level Layout

```text
apps/
  api/          FastAPI transport layer
  web/          Next.js 14 UI
  workers/      async worker runtime
src/
  dietary_guardian/
    core/       tiny shared primitives
    features/   product behavior and service entrypoints
    agent/      bounded model/provider logic
    platform/   persistence + integrations
    shared/     shared utilities (time, etc.)
docs/           canonical docs
tests/          unit/integration/e2e
```

## 2. Key Entrypoints

- **API app**: `apps/api/dietary_api/main.py`
- **API routing**: `apps/api/dietary_api/routers/`
- **API deps/context**: `apps/api/dietary_api/deps.py`
- **API policy**: `apps/api/dietary_api/policy.py`
- **Web app**: `apps/web/app/`
- **Workers**: `apps/workers/run.py`, `apps/workers/reminder_worker.py`

## 3. Feature Layer (Product Behavior)

Location: `src/dietary_guardian/features/`

Key modules:
- **companion/**: core care-loop modules
  - `core/` (case snapshot + evidence/health state)
  - `personalization/`, `engagement/`, `care_plans/`
  - `clinician_digest/`, `impact/`, `interactions/`
- **meals/**: meal analysis + records
- **recommendations/**: daily suggestions + substitutions
- **reminders/**: reminders + notifications/outbox
- **medications/**: regimens + adherence
- **reports/**: biomarker parsing + reports
- **symptoms/**, **profiles/**, **households/**, **safety/**

Feature entrypoints are typically `service.py` or `use_cases.py` under each feature.

## 4. Agent Layer (Bounded AI)

Location: `src/dietary_guardian/agent/`

Modules:
- **chat/**: companion chat pipeline
  - `agent.py` (ChatAgent), `router.py` (query routing)
  - `audio.py`, `emotion.py`, `health_tracker.py`, `memory.py`
- **meal_analysis/**: meal perception pipeline
- **dietary/**: dietary claims extraction
- **vision/**: hawker vision module
- **emotion/**: canonical emotion inference runtime
- **recommendation/**: recommendation agent
- **shared/**: LLM/runtime abstractions

Agents do not own durable state; they enrich or propose.

## 5. Platform Layer (Infrastructure)

Location: `src/dietary_guardian/platform/`

Key areas:
- **persistence/**: SQLite repositories + ingestion
- **auth/**: sessions + signers
- **cache/**: in-memory/redis stores
- **messaging/**: notification channels + outbox
- **scheduling/**: worker coordination
- **storage/**: media upload/ingestion
- **observability/**: logging + tooling + workflows

## 6. Data & Runtime Artifacts

- **Static datasets**: `src/dietary_guardian/data/`
  - `food/` (sg_hawker_food, drinks)
  - `clinical/` (ACE PDFs)
  - `emotion/` (support metadata)
- **Runtime**: `data/runtime/` and `data/vectorstore/` (git-ignored)

## 7. Tests

```text
tests/unit/
tests/integration/
tests/e2e/
```

## 8. Extension Pointers

- Add new product behavior under `features/<feature>/service.py`
- Add new model/runtime logic under `agent/<agent>/`
- Add new infra integration under `platform/<area>/`
- Keep routers thin: map requests to feature services
