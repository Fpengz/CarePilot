# Codebase Walkthrough

Last updated: 2026-03-06  
See also: [`docs/system-overview.md`](../docs/system-overview.md), [`ARCHITECTURE.md`](../ARCHITECTURE.md)

## Repository Structure

```text
apps/
  api/dietary_api/        FastAPI app, routers, API services, schemas
  web/                    Next.js app, components, typed API client
  workers/                Worker runtime entrypoint
src/dietary_guardian/
  agents/                 Agent/provider logic
  application/            Use-case boundaries and ports
  config/                 Runtime settings
  infrastructure/         Persistence/cache/coordination adapters
  models/                 Shared typed domain contracts
  safety/                 Safety and triage utilities
  services/               Core orchestration and domain services
docs/                     Canonical docs and runbooks
scripts/                  Unified developer CLI and operational scripts
tests/                    Repository-level tests
apps/api/tests/           API contract and behavior tests
```

## Backend Walkthrough

### API Entrypoints
- `apps/api/dietary_api/main.py`: app factory, middleware, router mounting.
- `apps/api/dietary_api/routers/__init__.py`: router composition.
- `apps/api/dietary_api/routes_shared.py`: shared auth/session/action helpers.

### Router Layer
- Path: `apps/api/dietary_api/routers/*.py`.
- Responsibility: transport mapping, auth guard checks, response model mapping.
- Pattern: thin routers calling service-layer functions.

### API Service Layer
- Path: `apps/api/dietary_api/services/*.py`.
- Responsibility: endpoint-specific orchestration, model shaping, workflow calls.
- Notable modules:
  - `workflows.py`
  - `meals.py`
  - `medications.py`
  - `symptoms.py`
  - `reports.py`
  - `clinical_cards.py`

### Schema Contracts
- Path: `apps/api/dietary_api/schemas.py`.
- Responsibility: request and response typing for API contracts.

## Core Domain and Service Modules

### Orchestration and Workflow
- `src/dietary_guardian/services/workflow_coordinator.py`: workflow execution, replay, and timeline integration.
- `src/dietary_guardian/services/agent_registry.py`: agent and workflow runtime contract catalog.
- `src/dietary_guardian/services/policy_service.py`: role/agent/tool policy evaluation.

### Agent and Tooling
- `src/dietary_guardian/agents/*`: provider-specific and agent-specific execution logic.
- `src/dietary_guardian/services/tool_registry.py`: registered tool invocation boundary.
- `src/dietary_guardian/services/platform_tools.py`: side-effectful platform tool implementations.

### Health Feature Services
- Meals/nutrition: daily + weekly summary services.
- Recommendations: adaptive ranking and interaction ingestion.
- Reminders/medications: scheduling, adherence, and delivery tracking.
- Symptoms/reports/clinical cards: symptom aggregation and report context synthesis.

## Data Models and Persistence

### Models
- Path: `src/dietary_guardian/models/*.py`.
- Defines typed contracts for:
  - user/profile/auth concepts,
  - meals/nutrition,
  - medication/adherence/reminders,
  - workflow/timeline events,
  - policy and contract snapshots.

### Persistence and Data Adapters
- Path: `src/dietary_guardian/infrastructure/persistence/*`.
- Backends:
  - SQLite baseline adapters.
  - Postgres schema and adapter implementation.
- Postgres schema entrypoint:
  - `postgres_schema.py`.

### Ephemeral State and Coordination
- Path:
  - `src/dietary_guardian/infrastructure/cache/redis_store.py`
  - `src/dietary_guardian/infrastructure/coordination/redis_coordination.py`
- Supports Redis-backed cache/coordination with v2 keyspace contracts.

## Frontend Walkthrough

### App and Routes
- Path: `apps/web/app/*`.
- Primary route surfaces:
  - dashboard/settings
  - meals/reminders/medications
  - symptoms/reports/clinical-cards/metrics
  - workflows governance and trace inspection

### API Integration
- `apps/web/lib/api/*.ts`: domain-scoped typed API clients (`auth`, `profile`, `household`, `meal`, `recommendation`, `reminder`, `workflow`).
- `apps/web/lib/api.ts`: compatibility-only consolidated client (temporary migration shim).
- `apps/web/lib/types.ts`: client-side API response type contracts.

### Component Layer
- `apps/web/components/*`: reusable UI primitives and feature components.

## Worker Runtime
- Entry: `apps/workers/run.py`.
- Purpose: external scheduler/outbox/dispatch loop for asynchronous operations.
- Used by smoke and target-aligned dev flows.

## When to Update This Document
- New top-level modules or major directory reshaping.
- Changes to ownership boundaries between routers/services/domain/infrastructure.
- New worker/runtime topology or orchestration engine changes.
