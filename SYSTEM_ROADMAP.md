# CarePilot System Roadmap

## Purpose
This is the single source of truth for CarePilot's development, combining architectural vision, technical debt management, and active implementation plans.

## Current Maturity
Implemented baseline:
- FastAPI API with auth, policy, and workflow trace support.
- Next.js frontend with impeccable UI redesign.
- Feature-first modular monolith backbone.
- LangGraph-based ChatOrchestrator with streaming support.
- Meal analysis, medication management, reminders, and health metrics.
- SQLite default persistence.

---

## 1. Today's Plan (Active Workstreams)

### 1.1 Multi-Agent & Chat Refinement
- [ ] **Fast-Path Intent Gate**: Skip heavyweight LangGraph for simple social/low-intent queries.
- [ ] **Context Pruning**: Implement relevance-based and temporal pruning in `PatientCaseSnapshot`.
- [ ] **ChatAgent Consolidation**: Finalize the core refactor of `ChatOrchestrator` and remove legacy handler leftovers.
- [ ] **EmotionAgent Workflow**: Centralize emotion inference in a single runtime with clear enable/disable flags.

### 1.2 Infrastructure Hardening
- [ ] **Protocol Migration**: Replace `getattr` magic in repositories (e.g., `alert_outbox.py`) with strict Python Protocols.
- [ ] **Transactional Timeline Writes**: Move timeline writes into an outbox-backed persistence path to ensure reliability.
- [ ] **Feature Flags**: Migrate environment-based guards to structured `FeatureFlags` in `AppSettings`.

### 1.3 Message Channels (OpenClaw-style)
- [ ] **Generalize Channels**: Rename domain contracts to `Message*` and add attachment support.
- [ ] **Inbound Ingestion**: Add full-duplex inbound support (e.g., Telegram webhooks).
- [ ] **Welcome Flow**: Send an outbound welcome message when a new channel is linked.

---

## 2. Production-Ready Gaps & Technical Debt

### 2.1 Reliability & Schema Management
- **Schema Migrations**: Introduce a formal migration tool (Alembic) to replace the current 'init if not exists' pattern.
- **Outbox Pattern**: Ensure all side effects (logs, notifications) are transactional with state changes.

### 2.2 Observability & Performance
- **Logging Alignment**: Ensure all agents and services use the centralized `setup_logging` consistently.
- **Snapshot Bottleneck**: Transition `PatientCaseSnapshot` generation to a background-projected read model (projection sections).
- **Validation Overhead**: Consolidate Pydantic models to reduce redundant validation across agent/service boundaries.

### 2.3 Security & Testing
- **Memory Isolation Audit**: Continue auditing cross-user isolation for memory and health profiles.
- **E2E Validation**: Ensure all core flows (Meal → Meds → Reminders → Chat) pass in `web-e2e`.
- **LLM Evaluation**: Implement automated evaluation for agent reasoning quality.

---

## 3. Architectural North Star

### Ownership Rule
- **features/**: Own product behavior and deterministic domain rules.
- **agent/**: Own model-backed inference (no direct writes/DB access).
- **platform/**: Own infra-only adapters (Auth, Cache, Storage).
- **core/**: Own cross-cutting contracts and tiny primitives.

### Target Feature Shape
```text
features/<feature>/
  domain/         # models, deterministic rules, persistence
  workflows/      # LangGraph (multi-step journeys)
  use_cases/      # application entrypoints
  presenters/     # domain → feature-view models
  ports.py        # protocols for dependency inversion
```

---

## 4. Documentation & Submission Prep
- [ ] **Technical Overview**: Generate Product + Technical Overview for Hackathon entry.
- [ ] **Prompt Catalog**: Document all LLM prompts in `docs/prompt_catalog.md`.
- [ ] **Architecture Diagrams**: Update Mermaid diagrams in `ARCHITECTURE.md`.
