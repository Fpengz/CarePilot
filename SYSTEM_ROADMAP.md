# CarePilot System Roadmap

## Canonical Documentation

| Doc | Status | Last Verified | Owner |
| --- | --- | --- | --- |
| `SYSTEM_ROADMAP.md` | active | 2026-04-01 | platform |
| `README.md` | active | 2026-04-01 | platform |
| `ARCHITECTURE.md` | active | 2026-04-01 | platform |
| `AGENTS.md` | active | 2026-04-01 | platform |
| `docs/README.md` | active | 2026-04-01 | platform |
| `docs/ARCHITECTURE_AND_ROADMAP.md` | active | 2026-04-01 | platform |

## Purpose
This is the single source of truth for CarePilot's development, combining architectural vision, technical debt management, and active implementation plans.

Related docs:
- `docs/exec-plans/index.md`
- `docs/design-docs/index.md`

## Current Maturity
Implemented baseline:
- FastAPI API with auth, policy, and workflow trace support.
- Next.js frontend with impeccable UI redesign.
- Event-driven workflow spine with LangGraph for explicit journeys (orchestration-first is legacy).
- SQLModel persistence with formal Alembic migrations (SQLite backend today).
- Strict Protocol-based repository interfaces.

---

## April 1, 2026 — Current Snapshot

### Completed
- Harness engineering principles adopted across docs and validation workflows.
- Unified observability implemented with Logfire across FastAPI, SQLModel, and HTTPX.
- Automated project versioning and repository housekeeping (stale plan promotion).
- Legacy SQLite persistence migrated to SQLModel + Alembic with normalized tables.
- Mandatory validation gate established via pre-commit hooks (100% E2E pass).

### Current Priorities
- Production hardening: predictable worker scheduling and health checks.
- User health mitigation: improve clinician summaries and adherence guidance.
- Retire remaining orchestration-first assumptions; keep legacy artifacts as reference only.

## 1. Recently Completed (Milestone: Foundational Stability)

### 1.1 Agent & Chat Consolidation
- **ChatAgent Consolidation**: Cleaned up legacy handlers in `ChatOrchestrator`; inference now flows through supervisor-led LangGraph.
- **EmotionAgent Centralization**: Unified text/speech emotion inference in a single runtime.

### 1.2 Structural Hardening (Relational Maturity)
- **Database Normalization**: Migrated `UserProfileRecord` fields (goals, schedules) to relational tables.
- **Alembic Integration**: Fully versioned schema management.

### 1.3 Messaging & Multi-Modal Integration
- **Full-Duplex Inbound**: Telegram webhooks and inbound processing active.
- **Attachment Support**: Consistent image/audio handling across channels.

### 1.4 Quality Assurance & Observability
- **E2E Validation**: 12/12 Playwright flows passing.
- **Unified Tracing**: Logfire instrumentation for API, Workers, and Inference.
- **Validation Gate**: Mandatory pytest/playwright pass before commit.
- **Alembic Integration**: Migrated from manual SQLite initialization to formal versioned migrations.
- **Auth Store Hardening**: Refactored `InMemoryAuthStore` and `SQLiteAuthStore` with structured settings and auto-seeding.
- **API Type Safety**: Resolved 25+ type-checking diagnostics across the backend using `ty`.
- **Frontend Restoration**: Restored missing `pnpm` dependencies, fixed ESLint flat config, and resolved React/TypeScript mismatches.
- **Dashboard Refactor**: Implemented a functional `DashboardPage` following the new feature-first architecture.
- **Context Pruning**: Implemented relevance-based and temporal pruning in `PatientCaseSnapshot`.

---

## 3. Archived / Deferred Tasks
- **Fast-Path Intent Gate**: (Archived) Low-intent query skipping.
- **Transactional Timeline Writes**: (Archived) Outbox-backed timeline persistence.
- **Welcome Flow**: (Archived) Automatic outbound welcome messages.
- **Outbox Pattern**: (Archived) General side-effect transactionality.
- **Logging Alignment**: (Archived) Standardizing `setup_logging` across all services.
- **Validation Overhead**: (Archived) Pydantic model consolidation.
- **Memory Isolation Audit**: (Archived) Deep dive into cross-user memory leakage.
- **LLM Evaluation**: (Archived) Automated reasoning quality harness.
- **Documentation Prep**: (Archived) Technical Overview and Architecture Diagram updates.

---

## 4. Architectural North Star
- **features/**: Own product behavior and deterministic domain rules.
- **agent/**: Own model-backed inference (no direct writes/DB access).
- **platform/**: Own infra-only adapters (Auth, Cache, Storage).
- **core/**: Own cross-cutting contracts and tiny primitives.
