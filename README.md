# Dietary Guardian SG

Dietary Guardian SG is a refactored AI health companion platform for chronic-condition support outside the clinic. It combines longitudinal patient context, deterministic health reasoning, evidence-backed guidance, clinician-facing digests, and measurable impact tracking in a modular-monolith architecture.

## 1. System Overview

### Purpose of the Project
This project exists to help patients manage chronic conditions between clinical visits. The system is designed as an AI health companion that can support daily decision-making, reinforce adherence, detect patterns that need attention, and surface concise clinician-ready summaries when follow-up is warranted.

### Problem the System Solves
Patients dealing with diabetes, hypertension, hyperlipidemia, medication routines, symptoms, and report follow-ups often face the same problems:
- guidance is fragmented across meals, medications, symptoms, and lab reports
- follow-through drops when advice is not contextual or realistic
- clinicians do not see a clean summary of what changed, what was tried, and what still needs attention
- health improvement is hard to measure without a structured baseline and follow-up view

Dietary Guardian addresses that by turning scattered health signals into one companion workflow.

### Key Capabilities of the AI Health Companion
- builds a longitudinal patient snapshot from meals, reminders, adherence events, symptoms, biomarkers, and profile context
- accepts typed companion interactions through:
  - `chat`
  - `meal_review`
  - `check_in`
  - `report_follow_up`
  - `adherence_follow_up`
- personalizes guidance based on current risk, barriers, emotional tone, and local Singapore food context
- retrieves supporting evidence through an internal evidence boundary before composing guidance
- runs deterministic safety review before returning user-visible recommendations
- generates clinician digests with:
  - summary
  - why now
  - priority
  - what changed
  - interventions attempted
  - supporting citations
- tracks impact using baseline/comparison windows and delta-oriented metrics

## 2. Architecture Overview

### High-Level Architecture
The refactored system is a modular monolith with clear domain, application, infrastructure, transport, and frontend boundaries.

Primary layers:
- `apps/web` provides the patient and reviewer-facing interface
- `apps/api` provides the FastAPI transport layer
- `src/dietary_guardian/domain` defines typed companion contracts
- `src/dietary_guardian/application` contains use-case orchestration and reasoning
- `src/dietary_guardian/infrastructure` contains persistence, auth, coordination, emotion, and evidence adapters
- `apps/workers` runs asynchronous reminder and outbox processing

### Target System Architecture
The intended target shape is a layered companion platform rather than a direct mirror of the repository layout.

Architectural intent:
- frontend UI and messaging channels act as client entry points
- FastAPI remains a thin API gateway for auth, policy, transport validation, and request shaping
- workflow coordination and application orchestration sit above the core health reasoning services
- agent orchestration is bounded behind typed contracts and used only for specialized reasoning
- business logic lives in health reasoning, recommendation, ingestion, and notification services instead of route handlers
- PostgreSQL is the durable system of record and Redis handles cache, queue, and coordination concerns
- async workers process notifications, ingestion pipelines, indexing, replay, and other background jobs
- all LLMs, messaging vendors, and third-party APIs remain outside the core system behind integration boundaries

A `draw.io` system architecture diagram should replace the removed Mermaid diagram in a future documentation update.

### Major Subsystems

#### Frontend
- Next.js application in `apps/web`
- companion-first surfaces:
  - `/companion`
  - `/clinician-digest`
  - `/impact`
- typed API client lives in `apps/web/lib/api`

#### API Layer
- FastAPI app in `apps/api/dietary_api`
- thin routers map requests to application services
- request/correlation IDs, auth, policy checks, and error handling live here

#### Application Layer
- `case_snapshot` builds the typed longitudinal health state
- `personalization` derives focus areas, barriers, tone, and intervention goals
- `engagement` scores current risk and support mode
- `evidence` retrieves supporting citations through an internal port
- `care_plans` composes interaction-type-specific guidance
- `safety` performs deterministic approval/adjustment/escalation review
- `clinician_digest` generates low-burden clinical summaries
- `impact` computes baseline/comparison metrics and deltas
- `interactions` orchestrates the full companion flow

#### Agents and Specialized Logic
- `src/dietary_guardian/agents` contains LLM/provider-specific and health-assistance logic
- current agent-oriented logic is bounded and not allowed to bypass deterministic contracts
- the system treats agents as helpers, not as the source of truth for durable health state

#### Workflow and Background Execution
- event timelines and workflow traces are recorded in the API/runtime layer
- `apps/workers/run.py` runs the external worker loop for outbox, reminders, and related async operations
- the worker includes in-process retry behavior for transient loop failures

#### Storage and Runtime Infrastructure
- default durable storage is SQLite
- persistence ownership lives in `src/dietary_guardian/infrastructure/persistence`
- app-store selection is backend-neutral and can target SQLite or PostgreSQL
- Redis-backed coordination/cache remains the scale-later path where configured
- evidence retrieval is currently behind `src/dietary_guardian/infrastructure/evidence`

### Data and Control Flow
The main companion flow is:

1. The frontend sends a request to the FastAPI API.
2. The API authenticates the session, checks scopes, and attaches request/correlation IDs.
3. The companion service loads raw patient state from the configured stores.
4. The application orchestrator builds:
   - `CaseSnapshot`
   - `PersonalizationContext`
   - `EngagementAssessment`
5. The orchestrator retrieves supporting evidence through `EvidenceRetrievalPort`.
6. The care-plan module generates an interaction-type-specific response.
7. The safety module approves, adjusts, or escalates that plan.
8. The clinician digest and impact summary are generated from the same result bundle.
9. The API returns typed JSON responses to the frontend.
10. Worker-driven async flows continue reminders, notifications, and future proactive support.

## 3. Project Structure

### Repository Layout
```text
apps/
  api/
    dietary_api/
      main.py
      deps.py
      middleware.py
      policy.py
      routers/
      schemas/
      services/
    tests/
  web/
    app/
    components/
    e2e/
    lib/
  workers/
src/
  dietary_guardian/
    agents/
    application/
      case_snapshot/
      personalization/
      engagement/
      evidence/
      care_plans/
      safety/
      clinician_digest/
      impact/
      interactions/
    config/
    domain/
      care/
    infrastructure/
      auth/
      cache/
      coordination/
      emotion/
      evidence/
      persistence/
    models/
    observability/
    safety/
    services/
docs/
scripts/
tests/
```

### Responsibilities of Key Modules
- `apps/api/dietary_api/routers/`: transport-only HTTP routes
- `apps/api/dietary_api/services/`: API-facing request shaping and delegation into application logic
- `apps/web/app/`: route-level pages for the companion UI
- `apps/web/lib/api/`: typed web client modules
- `src/dietary_guardian/domain/care/`: canonical typed contracts for companion flows
- `src/dietary_guardian/application/`: system behavior and orchestration
- `src/dietary_guardian/infrastructure/persistence/`: repository and app-store implementations
- `src/dietary_guardian/infrastructure/evidence/`: current evidence adapter(s)
- `src/dietary_guardian/agents/`: bounded model/provider logic
- `apps/workers/`: external async worker runtime
- `scripts/dg.py`: unified developer CLI for dev, test, infra, and validation workflows

## 4. Core Components

### Agent System
The project uses narrow agents and provider-specific helpers under `src/dietary_guardian/agents`.

Current role of the agent layer:
- meal-related perception and reasoning helpers
- provider selection and model integration
- bounded assistive logic where deterministic code is not enough

Architectural rule:
- agents propose or enrich; they do not own durable health state
- typed contracts and deterministic safety always take precedence

### Workflow Orchestration
The main orchestration path for the refactored companion lives in:
- `src/dietary_guardian/application/interactions/use_cases.py`

It coordinates:
- state loading inputs from the API service
- case snapshot construction
- personalization
- engagement scoring
- evidence retrieval
- care plan composition
- safety review
- clinician digest generation
- impact summary generation

### Health Reasoning Modules
These modules form the core reasoning spine:
- `application/case_snapshot`: fuses meals, reminders, adherence, symptoms, and biomarkers into one longitudinal state
- `application/personalization`: translates patient state and message intent into focus areas, barriers, tone, and intervention goal
- `application/engagement`: scores near-term risk and recommended support mode
- `application/safety`: enforces deterministic approval, adjustment, or escalation

### Recommendation and Monitoring Services
These modules translate state into action and measurement:
- `application/care_plans`: produces actionable, interaction-type-specific guidance
- `application/clinician_digest`: produces a clinician-readable summary with priority and evidence
- `application/impact`: produces tracked metrics, deltas, and measured intervention windows
- `apps/workers`: continues reminders, outbox work, and async delivery patterns

## 5. Running the System

### Setup Instructions
Prerequisites:
- Python 3.12+
- `uv`
- `pnpm`
- Docker, if using local PostgreSQL/Redis infrastructure

Install dependencies:
```bash
uv sync
pnpm install
```

Create local environment file:
```bash
cp .env.example .env
```

Minimum local settings:
- `AUTH_STORE_BACKEND=sqlite`
- `API_SQLITE_DB_PATH=dietary_guardian_api.db`
- `AUTH_SQLITE_DB_PATH=dietary_guardian_auth.db`
- `LLM_PROVIDER=ollama` or `LLM_PROVIDER=vllm` or a cloud provider
- `LOCAL_LLM_BASE_URL` for local providers

### Development Environment
Unified full-stack dev command:
```bash
uv run python scripts/dg.py dev
```

Useful variants:
```bash
uv run python scripts/dg.py dev --no-web
uv run python scripts/dg.py dev --no-api
uv run python scripts/dg.py dev --no-scheduler
```

Primary local endpoints:
- web: `http://localhost:3000`
- API docs: `http://localhost:8001/docs`

### How to Start Backend, Workers, and Frontend

Backend only:
```bash
uv run python -m apps.api.run
```

Frontend only:
```bash
pnpm web:dev
```

Worker only:
```bash
pnpm dev:worker
```

Optional target-aligned local infra:
```bash
uv run python scripts/dg.py infra up
uv run python scripts/dg.py migrate postgres
```

Helpful developer commands:
```bash
uv run python scripts/dg.py help
uv run python scripts/dg.py readiness http://127.0.0.1:8001
uv run python scripts/dg.py smoke postgres-redis
```

Validation commands:
```bash
uv run ruff check .
uv run ty check . --extra-search-path src --output-format concise
uv run pytest -q
pnpm web:lint
pnpm web:typecheck
pnpm web:build
```

## 6. Extending the System

### How to Add New Agents
Add new bounded agent/provider logic under:
- `src/dietary_guardian/agents/`

Rules:
- agents must operate behind typed inputs and outputs
- they must not write durable state directly
- they must not bypass deterministic safety or policy decisions
- they should be invoked from application-layer orchestration, not directly from routers

### How to Add New Tools or Modules
For new business capabilities:
- put transport concerns in `apps/api/dietary_api/routers/` or `apps/api/dietary_api/services/`
- put system behavior in `src/dietary_guardian/application/`
- put shared contracts in `src/dietary_guardian/domain/`
- put storage/adapters in `src/dietary_guardian/infrastructure/`

Examples:
- new reasoning workflow: add an application module and wire it through the orchestrator
- new retrieval or external integration: add an infrastructure adapter behind a port
- new persistence backend: extend infrastructure persistence builders/contracts
- new frontend workflow: add a route in `apps/web/app/` and a typed client in `apps/web/lib/api/`

### Where New Features Should Be Integrated
Use these integration rules:
- patient-facing interaction logic belongs in `application/interactions`
- state fusion belongs in `application/case_snapshot`
- guidance generation belongs in `application/care_plans`
- evidence retrieval belongs behind `application/evidence` ports
- deterministic review belongs in `application/safety`
- clinician-facing summaries belong in `application/clinician_digest`
- outcome measurement belongs in `application/impact`
- route handlers should stay thin and delegate to application services

## References
- `ARCHITECTURE.md` for the canonical architecture document
- `SYSTEM_ROADMAP.md` for the active refactor and delivery roadmap
- `AGENTS.md` for multi-agent workflow rules
- `CONTRIBUTING.md` for repo standards
- `docs/config-reference.md` for environment configuration
- `docs/README.md` for the broader documentation index
