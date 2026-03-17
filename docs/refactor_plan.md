# CarePilot Refactor Plan (Single Source of Truth)

**Status:** Active (Phase 1 complete)  
**Principle:** **feature-first modular monolith** with a small typed inference layer  
**Backward compatibility:** **not required** (renames/deletes are allowed)

This document is the canonical plan. Any other refactor-plan docs should be treated as deprecated pointers to this file.

---

## 0) Current State (As Of 2026-03-14)

Completed in Phase 1:

- Removed central coordinator + contract snapshot mechanism (done)
- Updated hot-path callers to emit traces directly to `EventTimelineService` (done)
- Added feature-owned workflow trace primitives (done)
- Removed workflow governance endpoints (done)
- Enforced “coordinator/snapshots are gone” via meta tests (done)

Completed in Phase 1.5 (Agent Layer Audit & Refactor):

- **Audited and refactored all agents** (`src/care_pilot/agent/**`) to be inference-only:
  - Standardized on `pydantic_ai` for model-backed agents.
  - Removed orchestration, persistence, and domain writes from all agents.
  - Moved generic input/output schemas from `features/` to their respective `agent/` packages.
- **Dietary Agent**: Stripped of safety checks (moved to `features/safety`) and business logic.
- **Meal Analysis Agent**: Replaced heavy vision module with thin `MealPerceptionAgent`; moved normalization and persistence to `features/meals`.
- **Emotion Feature**: Moved the entire inference pipeline, adapters, and engine from `agent/emotion` to `features/companion/emotion`.
- **Chat Orchestration**: Extracted memory management, query routing, and stream pipeline from `ChatAgent` to `features/companion/chat/orchestrator.py`.
- **Recommendation Agent**: Slimmed down to an inference facade for the recommendation engine.
- **Meta-Test Guardrails**: Updated `tests/meta/test_agent_layer_boundaries.py` to strictly forbid LLM plumbing outside the agent layer and feature logic inside the agent layer.

Remaining boundary work:

- Many `src/care_pilot/features/**` modules still import API schemas and/or API context types (to be removed in Phase 2).
- Explicit `pydantic-graph` workflows for meals and medications (Phase 2).

Phase 2 status update:

- `pydantic-graph` introduced for declared workflows:
  - Meals: `features/meals/workflows/meal_upload_graph.py` is now the hot path for `/api/v1/meal/analyze`.
  - Medications: `features/medications/workflows/prescription_ingest_graph.py` scaffolded (still `not_implemented`).
- Provider selection + test seams restored for meal perception via `agent/meal_analysis/vision_module.py` (`HawkerVisionModule`), used inside the meal upload workflow to support provider routing tests and deterministic test-mode behavior.
- Chat streaming endpoints now use `ChatStreamRuntime.stream(...)` for token streaming (so tests can patch streaming without invoking LLM providers); feature orchestration remains in `features/companion/chat/**`.
- Emotion runtime loading is suppressed when inference is disabled (avoid heavyweight model loads in test/dev by default).

---

## 1) Repo-Wide Architecture Stance (Hard Decisions)

### 1.1 Primary rule (ownership)

Use this rule across the repo:

- **features** own product behavior
- **agent** owns inference implementations
- **platform** owns infra-only adapters
- **core** owns only tiny cross-cutting primitives

### 1.2 Standard libraries (to reduce refactor friction)

- **Inference agents:** standardize on `pydantic_ai` inside `src/care_pilot/agent/**` only.
- **Multi-step workflows:** standardize on `pydantic-graph` inside `src/care_pilot/features/**/workflows/**` only.
- **Scheduling/persistence/policy:** deterministic code in feature domain + platform adapters.
- **LangGraph:** explicitly deferred until we need checkpointed persistence, interrupts, or long-lived thread state as first-class requirements.

See `docs/workflows.md` for the decision table and workflow templates.

---

## 2) Canonical Feature Shape

Every feature should converge on:

```text
features/<feature>/
  domain/         # models, rules, deterministic services (incl. persistence writes)
  workflows/      # pydantic-graph workflows (multi-step journeys)
  use_cases/      # entrypoints/application services (single-step or thin workflow entrypoints)
  presenters/     # feature-level domain → view models (NOT apps/api schemas)
  ports.py        # feature-facing interfaces (protocols/ports)
```

Rules of thumb:

- **workflows** coordinate steps, branching, idempotency, tracing
- **domain** decides and writes (deterministic rules; persistence via stores)
- **use_cases** are the feature entrypoints the API calls
- **presenters** map domain → feature view models (API mapping stays in API layer)

---

## 3) What Counts As An Agent (And What Does Not)

### Agent definition

An agent is a **model-backed inference component** with:

- typed input schema
- typed bounded output schema (+ confidence, warnings, trace metadata)
- prompts/instructions
- inference wrapper (pydantic_ai runtime)

### Not an agent

- orchestration that sequences multiple steps (that’s a workflow)
- deterministic business rules (that’s domain logic)
- repositories, DB access, schedulers (platform / deterministic services)
- API request/response mapping

---

## 4) Target `agent/**` Shape (Smaller + Cleaner)

Target structure:

```text
agent/
  runtime/
  core/
  meal_analysis/
  dietary/
  medications/
  emotion/
  recommendation/
  chat/
```

Each agent package contains only:

- input/output schemas
- prompts/instructions
- inference wrapper
- agent-local helper logic
- trace/confidence/error handling

Agents must **not** contain:

- workflow orchestration
- persistence
- scheduling
- notification delivery
- API mapping
- domain writes

---

## 5) Strong Target Structure by Area

### 5.1 Meals

```text
features/meals/
  domain/
    models.py
    normalization.py
    nutrition.py
    persistence.py
  workflows/
    meal_upload_graph.py
    state.py
    output.py
  use_cases/
    analyze_meal.py
    list_meals.py
  presenters/
    api.py
  ports.py

agent/meal_analysis/
  meal_perception_agent.py
  schemas.py
  arbitration.py

agent/dietary/
  dietary_assessment_agent.py
  schemas.py
```

Meaning:

- meal perception + dietary reasoning remain separate agents
- normalization/nutrition/persist remain deterministic in meals domain
- orchestration lives in meals workflows

### 5.2 Medications + prescriptions + reminders

Boundary:

- medications feature owns **regimen truth**
- reminders feature owns **reminder truth**
- prescription ingest workflow bridges the two

```text
features/medications/
  domain/
    models.py
    regimen_normalization.py
    medication_scheduling.py
  workflows/
    prescription_ingest_graph.py
    state.py
    output.py
  use_cases/
    ingest_prescription.py
    manage_regimens.py
  presenters/
    api.py
  ports.py

agent/medications/
  prescription_extraction_agent.py
  schemas.py

features/reminders/
  domain/
    models.py
    generation.py
    materialization.py
  workflows/
    daily_generation_graph.py   # optional later
  use_cases/
    generate_reminders.py
    list_upcoming.py
  notifications/
    dispatch.py
  outbox/
    ...
  ports.py
```

### 5.3 Companion / chat / recommendation / emotion

Make `features/companion/**` the product spine; agents are supporting inference modules.

```text
features/companion/
  core/
    domain/
    snapshot/
    chat_context/
  chat/
    workflows/
    use_cases/
  recommendations/
    use_cases/
  emotion/
    use_cases/
  clinician_digest/
  care_plans/
  engagement/
  personalization/
  impact/

agent/chat/
agent/recommendation/
agent/emotion/
```

Meaning:

- features/companion owns journeys and composition
- agent/chat drafts/reasons
- agent/recommendation synthesizes
- agent/emotion infers emotion signals

---

## 6) Workflow Strategy (Graphs, Not God-Objects)

### Why graphs are needed

Some journeys are graph-shaped:

- sequencing across multiple bounded steps
- conditional branching
- retries/fallbacks
- step-level tracing

### What graphs must not absorb

- deterministic domain rules
- persistence writes
- infrastructure concerns

### Selected workflow runtime

- Use **`pydantic-graph`** for declared multi-step workflows.
- Do not adopt LangGraph now.

### LangGraph adoption criteria later

Only reconsider LangGraph if we need:

- durable long-lived thread state as a first-class operating model
- checkpoint/resume across long time gaps
- interrupt-heavy human-in-the-loop flows

---

## 7) Workflow Tracing Strategy (Canonical Sink)

### Decision

Use **`EventTimelineService`** as the canonical workflow trace sink.

### Why

Workflow traces are product-visible and operationally meaningful:

- replay by `correlation_id`
- timeline/audit display
- run lifecycle inspection
- stable observability independent of the workflow runtime internals

### Components

- Thin emitter: `src/care_pilot/features/workflows/trace_emitter.py`
- Trace query service: `src/care_pilot/features/workflows/query_service.py`
- Graph runner skeleton (for step tracing later): `src/care_pilot/features/workflows/graph_runner.py`

Do **not** use graph runtime persistence history as the canonical product audit trail.

---

## 8) Workflow Contract Snapshot Mechanism (Removed)

### Decision

**Remove it.**

### Removed surfaces

- workflow contract snapshot persistence
- snapshot CRUD APIs
- runtime-contract snapshot bootstrap

### Source of truth instead

- code-defined graphs
- typed input/state/output models
- docs + generated Mermaid diagrams
- tests
- git history

---

## 9) Delete / Rename / Merge (No Back-Compat)

### Delete / demote

- central workflow coordinator module (done)
- workflow contract snapshot CRUD (done)
- API response projectors outside API layer (in progress repo-wide)
- vague cross-feature forwarding wrappers that only forward calls (in progress repo-wide)

### Rename for clarity

- `service.py` → job names: `*_application_service.py`, `*_engine.py`, `*_query_service.py`
- `use_cases.py` → split into `use_cases/<use_case>.py` when broad
- `api_service.py` → move responsibility into API layer or feature workflow/use-case layer (no FastAPI types in features)

### Merge where it reduces ambiguity

- merge medication prescription modules into clearer workflows/use_cases structure
- merge “presenter” logic that is actually API schema mapping into API mappers

---

## 10) Repo-Wide Rules to Enforce (Hard Constraints)

1. Only `src/care_pilot/agent/**` may create or directly use `pydantic_ai` agents.
2. Only `src/care_pilot/features/**/workflows/**` may orchestrate multi-step journeys (pydantic-graph).
3. Only `src/care_pilot/features/**/domain/**` owns deterministic business rules and state transitions (incl. persistence writes).
4. `src/care_pilot/platform/**` may not import `src/care_pilot/features/**` or `src/care_pilot/agent/**`.
5. API layer maps request/response only and calls feature entrypoints.
6. No API schema imports inside `src/care_pilot/features/**` or `src/care_pilot/platform/**`.
7. Workflow traces go to `EventTimelineService` (via thin emitter where appropriate).

---

## 11) Meta Tests / Guardrails

Already implemented:

- Agent-layer LLM plumbing boundaries: `tests/meta/test_agent_layer_boundaries.py`
- Coordinator/snapshots removed: `tests/meta/test_workflow_coordinator_removed.py`

Next to add (Phase 1.5 / Phase 2):

- forbid `apps/api/carepilot_api/schemas` imports from `src/care_pilot/features/**` and `src/care_pilot/platform/**`
- forbid `pydantic_graph` imports outside `src/care_pilot/features/**/workflows/**`
- enforce platform import direction (platform never imports features/agent)

---

## 12) Refactor Order (Phased)

### Phase 1 — boundary cleanup (DONE)

- remove central coordinator
- remove snapshot mechanism
- ensure traces are timeline-backed
- remove coupled governance endpoints
- add meta tests

### Phase 2 — first explicit workflows (DONE)

- add `features/meals/workflows/meal_upload_graph.py` and route meal analysis through graph entrypoints
- add `features/medications/workflows/prescription_ingest_graph.py` bridging to reminders
- keep agents typed and small
- keep deterministic logic in feature domain modules

### Phase 2 — Status (DONE)

Completed:

- Meals are graph-owned: `/api/v1/meal/analyze` routes through `features/meals/workflows/meal_upload_graph.py`.
- Medications ingest graph scaffold exists: `features/medications/workflows/prescription_ingest_graph.py` (still returns `not_implemented`).
- `pydantic_ai` API usage updated repo-wide (output_type/result.output).
- `HawkerVisionModule` restored as a stable meal-perception facade for tests and thin callers: `agent/meal_analysis/vision_module.py`.
- Chat streaming endpoints use `ChatStreamRuntime.stream(...)` so tests can patch streaming without invoking remote LLM providers.
- Emotion runtime instantiation is suppressed unless inference is enabled (prevents heavyweight loads in default tests/dev).

Gates:

- `ruff`, `ty`, `pytest` pass.
- Note: pytest emits a non-fatal warning about a background `transformers` auto-conversion thread attempting network access.

### Phase 3 — companion spine and contract cleanup (DONE)

Goal: make `features/companion/**` the clear “product spine” with consistent feature shape, and keep `agent/**` as inference-only support.

Completed in Phase 3:

- **Canonical Contracts**: Relocated all API schemas from `apps/api/` to `src/care_pilot/core/contracts/api/`. Features now depend on these contracts instead of the API app, breaking reverse dependencies.
- **Orchestration Relocation**: Moved `context_loader.py` (now `companion_orchestration.py`) from the core feature layer to `apps/api/carepilot_api/services/`, correctly placing cross-feature aggregation in the API layer.
- **God Class Refactor**: Simplified `SQLiteRepository` by delegating to specialized domain repositories and centralizing schema bootstrap in `sqlite_bootstrap.py`.
- **Circular Import Resolution**: Extracted tool policy models to break the cycle between workflows and tooling domain models.
- **Infrastructure Stability**: Reconciled SQLite schemas with repository expectations and added missing delegation methods to satisfy domain store protocols.
- **Shared Utility Consolidation**: Moved timezone and clock helpers from `shared/time` to `core/time`, removing the redundant `shared/` package.

Gates:

- `ruff`, `ty`, `pytest` pass.
- All 14 medication intake API tests and core integration flows are stable.

### Phase 4 — naming and file cleanup (DONE)

- Replace generic `service.py` / `use_cases.py` / `presenter.py` where too broad.
- Standardize presenters/mappers to use `core/contracts/api/`.
- Clean up documentation and remove obsolete design artifacts.
- **Result**: 21+ files renamed to job-based conventions (e.g., `meal_service.py`, `medication_management.py`).

### Phase 5 — Documentation and Submission Prep (ACTIVE)

- Generate Product + Technical Overview for Singapore Innovation Challenge.
- Catalog all LLM prompts used in the system.
- Draft Hackathon Submission narrative aligned with Problem Statement #1.
- Update System Architecture diagrams (Mermaid + Draw.io instructions).
- Final cross-check of all `*.md` files for consistency.
- Validate system via `web-e2e` tests.

---

## 13) Naming Conventions (Repo-Wide)

Agents:

- `*_agent.py` (responsibility names)

Workflows:

- `*_graph.py`, `*_state.py`, `*_output.py`

Job-based services / Application services:

- `*_service.py` (e.g., `meal_service.py`, `reminder_service.py`)
- `*_management.py` (e.g., `medication_management.py`)
- `use_cases/<use_case>.py` for granular logic

Presenters/mappers:

- `presenters/api.py`, `*_mapper.py`, `*_presenter.py`


Domain engines:

- `*_engine.py`, `*_calculator.py`, `*_normalizer.py`, `*_validator.py`, `*_generator.py`

---

## 14) Validation / Acceptance

Minimum acceptance gates for each phase:

- meta tests enforcing rules (and updated when removing/renaming modules)
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run ruff check .`
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run ty check . --extra-search-path src --output-format concise`
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q`
