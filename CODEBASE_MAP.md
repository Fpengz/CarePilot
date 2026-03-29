# Codebase Map: care_pilots

> **Status**: Current (updated March 12, 2026)  
> **Scope**: Feature-first modular monolith with thin apps/ entrypoints.

## 0. Merge Provenance (Ervin + Xiangqi)

This codebase is the result of merging two Healthcare-Agent branches into the
feature-first architecture:

- **ervin branch (`healthcare/ervin`)**
  - Chat pipeline refactored into `src/care_pilot/agent/chat/`
  - API entrypoints: `apps/api/carepilot_api/routers/chat.py` and `dashboard.py`
  - Web entrypoint: `apps/web/app/chat/`
  - Food local retrieval ingester/retriever under `platform/persistence/food/`

- **xiangqi branch (`healthcare/xiangqi`)**
  - Hybrid food retrieval (vector + keyword rerank) refactored into
    `src/care_pilot/platform/persistence/food/hybrid_search.py`
  - Runtime artifacts (vectorstore/db) intentionally removed; they are now
    expected under `data/vectorstore/` at runtime only

## 1. Top-Level Layout

```text
apps/
  api/          FastAPI transport layer
  web/          Next.js 14 UI
  workers/      async worker runtime
src/
  care_pilot/
    core/       tiny shared primitives
    features/   product behavior and service entrypoints
    agent/      bounded model/provider logic
    platform/   persistence + integrations
    shared/     shared utilities (time, etc.)
docs/           system-of-record knowledge base (design docs, plans, specs, references)
tests/          unit/integration/e2e
```

## 2. Key Entrypoints

- **API app**: `apps/api/carepilot_api/main.py`
- **API routing**: `apps/api/carepilot_api/routers/`
- **API deps/context**: `apps/api/carepilot_api/deps.py`
- **API policy**: `apps/api/carepilot_api/policy.py`
- **Web app**: `apps/web/app/`
- **Workers**: `apps/workers/run.py`, `apps/workers/reminder_worker.py`

## 3. Feature Layer (Product Behavior)

Location: `src/care_pilot/features/`

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

Location: `src/care_pilot/agent/`

Modules:
- **core/**: base agent contracts and registry
- **runtime/**: inference engine, routing, model factory/types
- **chat/**: companion chat pipeline
  - `agent.py` (ChatAgent), `router.py` (query routing)
  - `audio_adapter.py`, `search_adapter.py`, `code_adapter.py`
  - `health_tracker.py`, `memory.py`, `routes/`
- **meal_analysis/**: meal perception pipeline
- **dietary/**: dietary claims extraction
- **emotion/**: canonical emotion inference runtime
- **recommendation/**: recommendation agent

Agents do not own durable state; they enrich or propose.

## 5. Platform Layer (Infrastructure)

Location: `src/care_pilot/platform/`

Key areas:
- **persistence/**: SQLite repositories + ingestion
- **auth/**: sessions + signers
- **cache/**: in-memory/redis stores
- **messaging/**: notification channels + outbox
- **scheduling/**: worker coordination
- **storage/**: media upload/ingestion
- **observability/**: logging + tooling + workflows

## 6. Data & Runtime Artifacts

- **Static datasets**: `src/care_pilot/data/`
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
