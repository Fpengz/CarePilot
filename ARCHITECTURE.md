# Architecture

## Purpose
This is the canonical architecture reference for CarePilot. It describes the feature-first modular-monolith structure, the ownership boundaries that contributors must preserve, and the forward direction for the project.

Related docs:
- `README.md`
- `docs/refactor_plan.md` — detailed refactor history and current status
- `docs/agent-modules.md` — agent layer deep-dive
- `docs/workflows.md` — workflow decision table and templates

---

## System Shape

CarePilot is a **feature-first modular monolith**: one codebase, strict layer ownership, no shared mutable globals. All work targets the canonical surfaces below.

```
src/care_pilot/
├── features/      product behavior and business entrypoints
├── agent/         bounded model-powered capabilities
├── platform/      infrastructure and runtime adapters
├── core/          shared primitives and contracts
└── config/        settings composition root
```

### Repo-Wide Architecture Stance (Hard Decisions)
- **Features** own product behavior.
- **Agent** owns inference implementations.
- **Platform** owns infra-only adapters.
- **Core** owns only tiny cross-cutting primitives.
- **Standard Libraries**:
  - **Inference agents**: Standardize on `pydantic_ai` inside `src/care_pilot/agent/**` only.
  - **Multi-step workflows**: Standardize on `pydantic-graph` inside `src/care_pilot/features/**/workflows/**` only.
  - **Scheduling/persistence/policy**: Deterministic code in feature domain + platform adapters.

---

## Layers

### Interface Layer — `apps/web/`
- Next.js 14 app router; typed API clients auto-generated from FastAPI schemas.

### API Layer — `apps/api/carepilot_api/`
- Owns HTTP transport, session auth, policy enforcement (`policy.py`), request validation, error mapping, and correlation IDs.
- Route handlers are transport-only: they validate, check policy, extract a scoped deps dataclass, and call a feature use-case function.
- **API Orchestrators**: Complex cross-feature aggregations for specific screens live in `apps/api/carepilot_api/services/` (e.g., `companion_orchestration.py`).
- **Never** put business logic in routers or router-level `Depends` chains.

### Worker Layer — `apps/workers/`
- Independent process consuming the reminder scheduler and alert outbox.
- Uses distributed locks from `platform/scheduling/coordination/` to prevent duplicate delivery.

### Feature Layer — `src/care_pilot/features/`
- Owns all product behavior. Every feature converges on:
  ```text
  features/<feature>/
    domain/         # models, rules, deterministic services (incl. persistence writes)
    workflows/      # pydantic-graph workflows (multi-step journeys)
    use_cases/      # entrypoints/application services (single-step or thin workflow entrypoints)
    presenters/     # feature-level domain → view models (NOT apps/api schemas)
    ports.py        # feature-facing interfaces (protocols/ports)
  ```
- **Workflows** coordinate steps, branching, idempotency, and tracing.
- **Domain** decides and writes (deterministic rules; persistence via stores).
- **Use cases** are the feature entrypoints the API calls.
- **Presenters** map domain → feature view models (API mapping stays in API layer).

### Agent Layer — `src/care_pilot/agent/`
- Bounded reasoning helpers. Agents propose; they never authorize delivery or write durable state directly.
- **Definition**: A model-backed inference component with typed input/output schemas, prompts, and a `pydantic_ai` wrapper.
- **Not an agent**: Orchestration, deterministic business rules, repository access, or API mapping.
- All agents inherit `BaseAgent[InputT, OutputT]` from `agent/core/` and return `AgentResult[OutputT]`.

### Platform Layer — `src/care_pilot/platform/`
- Infrastructure adapters. Feature code only touches platform through typed protocols or store interfaces.

### Config Layer — `src/care_pilot/config/`
- Single composition root (`app.py` → `AppSettings`). `get_settings()` validates cross-field constraints.

### Core Layer — `src/care_pilot/core/`
- Pure primitives: IDs, base errors, domain-neutral events, clock/time helpers.
- **Contracts**: `src/care_pilot/core/contracts/api/` defines the canonical Pydantic models for the API surface.

---

## Workflow Strategy

### Why Graphs Are Needed
- Sequencing across multiple bounded steps.
- Conditional branching, retries/fallbacks, and step-level tracing.
- Use **`pydantic-graph`** for declared multi-step workflows.

### Workflow Tracing
- Use **`EventTimelineService`** as the canonical workflow trace sink.
- Workflow traces are product-visible and operationally meaningful (replay by `correlation_id`, audit display).

---

## Request Lifecycle

```
Client
  │
  ▼
apps/api/carepilot_api/  ← authenticate session, check policy, validate input
  │
  ▼
features/<feature>/use_cases.py  ← load CaseSnapshot, orchestrate domain logic
  │              │
  │              ▼
  │        features/safety/  ← deterministic safety screen
  │
  ├──► agent/<agent>/  ← propose enriched output (never writes state)
  │
  ├──► features/companion/  ← personalization, engagement, clinician digest
  │
  ▼
platform/persistence/  ← persist durable outputs
platform/messaging/    ← emit follow-up work to outbox
  │
  ▼
apps/workers/  ← process reminders, outbox, background tasks
```

---

## Key Architectural Rules

1. **Route handlers are transport-only.** Auth check → policy check → scoped deps → call use case.
2. **Business logic lives in feature use cases/domain**, not in routers or UI glue.
3. **Domain layer is pure.** `features/*/domain/` has no I/O and no infrastructure imports.
4. **Agents are bounded helpers.** They receive typed input, return `AgentResult`, and never touch stores.
5. **Safety is deterministic.** `features/safety/domain/engine.py` runs before any LLM output is accepted.
6. **Platform adapters are the only I/O boundary.** Feature code does not open connections directly.
7. **Contracts break reverse dependencies.** Features return models from `core/contracts/api/` to avoid depending on the API app.
8. **No API schema imports** inside `src/care_pilot/features/**` or `src/care_pilot/platform/**`.

---

## Runtime Model

- SQLite for durable storage (`care_pilot.db`, `care_pilot_auth.db`).
- In-memory fallbacks for cache and coordination when Redis is absent.
- Redis for ephemeral state, distributed locks, and worker signaling in production-aligned environments.
- Chat memory and vector stores persist under `data/runtime/` and `data/vectorstore/`.
