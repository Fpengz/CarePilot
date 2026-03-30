# CarePilot System Roadmap

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

## March 29, 2026 — Current Snapshot

### Completed
- Harness engineering principles adopted across docs and validation workflows.
- Legacy SQLite persistence migrated to SQLModel + Alembic with normalized tables.
- Event-driven architecture established as the primary development direction.

### Current Priorities
- Production hardening: reliability, observability, and predictable worker scheduling.
- User health mitigation: improve clinician summaries, adherence guidance, and safety guardrails.
- Multi-channel messaging: inbound processing and attachment handling for real-time engagement.
- Retire remaining orchestration-first assumptions; keep legacy artifacts as reference only.
- Deployment topology and infra assumptions clarified in docs.

### Known Tech Debt
- Legacy doc references and root-level documentation drift (clean up and re-index).
- Optional infra assumptions (Redis/vector memory) are not consistently enforced or documented.
- Inference/runtime boundaries need clearer deployment guidance for production (API vs inference vs workers).

### Future Plans
- Production readiness: health checks, SLOs, and operational playbooks for API, workers, and inference.
- Health impact improvements: stronger personalization signals and longitudinal trend projections.
- Clinician support: richer digest, risk stratification, and export-ready summaries.

## 1. Today's Plan (Active Workstreams)

### 1.1 Agent & Chat Consolidation
- [ ] **ChatAgent Consolidation**: Clean up legacy handlers in `ChatOrchestrator` after the recent core refactor to ensure a single, maintainable inference path.
- [ ] **EmotionAgent Centralization**: Move speech and text emotion inference into a unified async runtime with clear enable/disable flags.

### 1.2 Structural Hardening (Relational Maturity)
- [ ] **Database Normalization**: Migrate `UserProfileRecord` JSON fields (conditions, medications, goals) into relational tables (`user_conditions`, `user_medications`, etc.) as per the 2026-03-27 design.

### 1.3 Messaging & Multi-Modal Integration
- [ ] **Full-Duplex Inbound**: Support Telegram webhooks and inbound message processing for real-time patient engagement.
- [ ] **Attachment Support**: Generalize message contracts to handle multi-modal attachments (images/audio) consistently across all channels.

### 1.4 Quality Assurance
- [ ] **E2E Validation**: Finalize and verify all core flows (Meal → Meds → Reminders → Chat) using the Playwright suite (`web-e2e`).

---

## 2. Recently Completed (Milestone: Hardening & Migration)
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
