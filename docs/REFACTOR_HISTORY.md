# CarePilot Refactor History

This document tracks the completed phases of the CarePilot architectural refactor.

## Phase 1 — Boundary Cleanup (Completed 2026-03-11)
- **Goal**: Break the tight coupling with the legacy central coordinator.
- **Actions**:
  - Removed central coordinator + contract snapshot mechanism.
  - Updated hot-path callers to emit traces directly to `EventTimelineService`.
  - Added feature-owned workflow trace primitives.
  - Removed workflow governance endpoints.
  - Enforced “coordinator/snapshots are gone” via meta tests.

## Phase 1.5 — Agent Layer Audit & Refactor (Completed 2026-03-12)
- **Goal**: Ensure agents are inference-only facades.
- **Actions**:
  - Standardized on `pydantic_ai` for model-backed agents.
  - Removed orchestration, persistence, and domain writes from all agents.
  - Moved generic input/output schemas from `features/` to their respective `agent/` packages.
  - Stripped **Dietary Agent** of safety checks (moved to `features/safety`).
  - Replaced **Meal Analysis Agent** heavy vision module with thin `MealPerceptionAgent`.
  - Extracted **Chat Orchestration** to `features/companion/chat/orchestrator.py`.

## Phase 2 — First Explicit Workflows (Completed 2026-03-13)
- **Goal**: Introduce `LangGraph` for multi-step journeys.
- **Actions**:
  - Meals: `features/meals/workflows/meal_upload_graph.py` is now the hot path for meal analysis.
  - Medications: Scaffolded `features/medications/workflows/prescription_ingest_graph.py`.
  - Restored `HawkerVisionModule` as a stable meal-perception facade.
  - Suppressed emotion runtime loading when inference is disabled to speed up dev/test.

## Phase 3 — Companion Spine and Contract Cleanup (Completed 2026-03-14)
- **Goal**: Relocate contracts and finalize feature shapes.
- **Actions**:
  - **Canonical Contracts**: Moved all API schemas to `src/care_pilot/core/contracts/api/`.
  - **Orchestration Relocation**: Moved cross-feature aggregation logic to the API layer.
  - **God Class Refactor**: Simplified `SQLiteRepository` by delegating to specialized domain repositories.
  - **Circular Import Resolution**: Extracted tool policy models to break dependency cycles.
  - **Shared Utility Consolidation**: Moved timezone and clock helpers to `core/time`.

## Phase 4 — Naming and File Cleanup (Completed 2026-03-15)
- **Goal**: Align file names with job-based conventions.
- **Actions**:
  - Renamed 21+ files (e.g., `service.py` → `meal_service.py`, `use_cases.py` → granular files).
  - Standardized presenters/mappers to use `core/contracts/api/`.
  - Removed obsolete design artifacts and cleaned up technical debt in documentation.

## Phase 7 — Early Wins (Completed 2026-03-19)
- **Actions**:
  - **Frontend Best Practices**: Migrated major pages to TanStack Query and implemented Vercel React Best Practices (dynamic imports, memoization, content-visibility).
  - **Backend Security**: Removed "Code Agent" for deterministic arithmetic, eliminating RCE risk in the dashboard.

## Phase 8 — Hardening and Relational Migration (Completed 2026-03-27)
- **Goal**: Move toward production-grade reliability and data integrity.
- **Actions**:
  - **Relational Profile Migration**: Normalized `UserProfileRecord` JSON fields into relational tables (`user_nutrition_goals`, `user_meal_schedule`) with full SQLModel and Alembic support.
  - **Full-Duplex Messaging**: Implemented Telegram webhook support (`/api/v1/webhooks/telegram`) and unified inbound/outbound message processing.
  - **Multi-Modal Sinks**: Enhanced the `TelegramChannel` sink to support audio and document attachments based on content types.
  - **Agent Consolidation**: Pruned 300+ lines of legacy code from `ChatOrchestrator`, ensuring all inference flows through the supervisor-led LangGraph.
  - **Unified Emotion Runtime**: Centralized text and speech emotion inference in `AppContext` for better latency and resource management.
  - **Frontend Build Restoration**: Resolved critical Tailwind v4/v3 mismatches and restored missing build-time dependencies.
  - **Type Safety**: Resolved 25+ backend type-checking diagnostics and fixed complex frontend React/TypeScript prop mismatches.
