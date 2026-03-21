# CarePilot Refactor Plan (Active)

**Status:** ACTIVE (Submission Prep & Hardening)  
**Architectural Principle:** **feature-first modular monolith**  
**Core Stack:** FastAPI, Next.js, TanStack Query, pydantic-ai, LangGraph

---

## 1) Current Status & Progress

| Phase | Goal | Status |
|---|---|---|
| **1-4** | Boundary Cleanup, Workflows, Contract Relocation, Naming | **COMPLETED** |
| **5** | Hackathon Submission & Documentation | **ACTIVE** |
| **6** | Multi-Agent Evolution (LangGraph + Supervisor) | **PLANNING** |
| **7** | Production Readiness & Performance | **IN PROGRESS** |

**Recent Wins (2026-03-19):**
- **Frontend**: Full migration to **TanStack Query**. Optimized bundle sizes and rendering performance (Next.js dynamic, content-visibility).
- **Security**: Eliminated dynamic code execution in dashboard trends.
- **Cleanup**: Consolidated refactor history into `docs/REFACTOR_HISTORY.md`.

---

## 2) Active Phase: Submission & Documentation (Phase 5)

**Goal**: Prepare the system for the Singapore Innovation Challenge hackathon submission.

- [ ] **Technical Overview**: Generate Product + Technical Overview for Challenge entry.
- [ ] **Prompt Catalog**: Document all LLM prompts used across agents in `docs/prompt_catalog.md`.
- [ ] **Architecture Diagrams**: Update Mermaid diagrams in `ARCHITECTURE.md` to reflect the new modular structure.
- [ ] **E2E Validation**: Ensure all core flows (Meal → Meds → Reminders → Chat) pass in `web-e2e`.

---

## 3) Active Phase: Production Hardening (Phase 7)

**Goal**: Address remaining critical performance and infrastructure technical debt.

### 7.1 Backend: Offload Heavy Inference
- **Status**: **COMPLETED** (2026-03-19)
- **Action**: Moved emotion inference to a dedicated microservice (`apps/inference/run.py`). Main API now uses `RemoteEmotionRuntime` to delegate heavy lifting.

### 7.2 Backend: Abstract Chat Orchestration
- **Status**: **COMPLETED** (2026-03-19)
- **Action**: Moved deep orchestration logic (streaming, emotion fusion, meal detection) from `chat.py` router to `ChatOrchestrator` service.

### 7.3 Frontend & Security Wins
- [x] **Code Agent Removal**: Replaced risky dynamic code execution with standard Python arithmetic.
- [x] **Best Practices**: Applied TanStack Query, dynamic imports, and memoization across all major pages.

---

## 4) Strategic Evolution: Multi-Agent System (Phase 6)

**Goal**: Transition from deterministic coordination to a **Supervisor-led LangGraph** system centered around a shared blackboard state.

### 6.1 Orchestration: Pivot to LangGraph
- **Decision**: Use **LangGraph** as the primary orchestration engine for complex, stateful multi-agent workflows.
- **Strategy**: Implement a **Supervisor-led** architecture where a top-level Orchestrator node decides the execution path.
- **Blackboard Model**: Use `PatientCaseSnapshot` as the shared `StateGraph` object. Agents read from and contribute to this structured memory.

### 6.2 Agent Contracts & Handoffs
- **Typed Handoffs**: Use `AgentRequest` / `AgentResponse` contracts (in `agent/core/contracts.py`) to standardize communication.
- **Supervisor Logic**: The Supervisor node uses `pydantic-ai` to interpret user intent and route to the appropriate specialist nodes (Meal, Meds, Trend, etc.).

### 6.3 Specialized Reasoning Agents
- **Perception Agents**: Promote existing Meal/Medication logic to inference-only perception nodes.
- **Reasoning Agents**:
    - **Trend Agent**: Extracts longitudinal patterns from biomarker/meal logs in the blackboard.
    - **Adherence Agent**: Reasons about medication behavior and proposes nudge strategies.
    - **Care Plan Agent**: Generates actionable clinician-aligned next steps based on the full clinical context.

---

## 5) Architectural North Star

### Ownership Rule
- **features/**: Own product behavior and deterministic domain rules.
- **agent/**: Own model-backed inference (no writes, no DB, no orchestration).
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

## 6) Hard Constraints (Meta-Test Enforced)

1. **Inference Boundary**: LLM logic lives *only* in `src/care_pilot/agent/**`.
2. **Orchestration Boundary**: Graph workflows live *only* in `src/care_pilot/features/**/workflows/**` (standardized on LangGraph for Phase 6+).
3. **Contract Boundary**: No API schema imports allowed inside `features/` or `platform/`. Use `core/contracts/api/`.
4. **Platform Purity**: Platform adapters cannot import features or agents.

---

## 7) Validation Gates

- `uv run ruff check .`
- `uv run ty check .`
- `uv run pytest -q`
- `pnpm web:typecheck`

---

*For detailed historical changes, see [Refactor History](./REFACTOR_HISTORY.md).*
