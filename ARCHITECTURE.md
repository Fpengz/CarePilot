# Architecture

## Purpose
This is the canonical architecture reference for CarePilot. It describes the current modular-monolith structure, the ownership boundaries that contributors must preserve, and the forward direction for the project.

Related docs:
- `README.md`
- `SYSTEM_ROADMAP.md`
- `docs/agent-modules.md` — agent layer deep-dive

---

## System shape

CarePilot is a **feature-first modular monolith**: one codebase, strict layer ownership, no shared mutable globals. All work targets the four canonical surfaces below.

```
src/care_pilot/
├── features/      product behavior and business entrypoints
├── agent/         bounded model-powered capabilities
├── platform/      infrastructure and runtime adapters
├── core/          shared primitives and contracts
└── config/        settings composition root
```

---

## Layers

### Interface layer — `apps/web/`
- Next.js 14 app router; typed API clients auto-generated from FastAPI schemas.
- Future messaging channels (WhatsApp, Telegram) integrate through the same API and workflow contracts.

### API layer — `apps/api/carepilot_api/`
- Owns HTTP transport, session auth, policy enforcement (`policy.py`), request validation, error mapping, and correlation IDs.
- Route handlers are transport-only: they validate, check policy, extract a scoped deps dataclass, and call a feature use-case function.
- **API Orchestrators**: Complex cross-feature aggregations for specific screens live in `apps/api/carepilot_api/services/` (e.g., `companion_orchestration.py`).
- **Never** put business logic in routers or router-level `Depends` chains.

### Worker layer — `apps/workers/`
- Independent process consuming the reminder scheduler and alert outbox.
- Uses distributed locks from `platform/scheduling/coordination/` to prevent duplicate delivery.

### Feature layer — `src/care_pilot/features/`
- Owns all product behavior. Each sub-package contains `domain/` (pure types + rules) and `use_cases.py` (orchestration).
- Feature code may call `agent/` and `platform/`, but `apps/` must not bypass feature use cases for business actions.
- **Dependency Rule**: Features must not depend on `apps/api`. They depend on `core/contracts/api/` for shared response models.

| Sub-package | Responsibility |
|-------------|----------------|
| `meals/` | Meal recognition, nutrition, daily/weekly summaries |
| `profiles/` | Health profiles, onboarding, role and social tools |
| `medications/` | Medication regimen scheduling, mobility reminders |
| `symptoms/` | Symptom check-in use cases |
| `safety/` | Deterministic safety engine, drug interactions, triage thresholds |
| `reminders/` | Reminder scheduling, notification materialization, multi-channel outbox |
| `reports/` | Biomarker PDF parsing and ingestion |
| `households/` | Multi-user household access policies |
| `recommendations/` | Daily recommendation engine (scoring + context + orchestration) |
| `companion/` | Patient engagement orchestration — see below |

**Companion sub-packages** (`features/companion/`):

| Sub-package | Responsibility |
|-------------|----------------|
| `core/` | `CaseSnapshot` read model, health analytics |
| `personalization/` | Preference-driven meal and lifestyle personalization |
| `engagement/` | Emotion-aware engagement, session tracking |
| `care_plans/` | Adaptive care plan generation |
| `clinician_digest/` | Clinical summary cards for practitioners |
| `impact/` | Health trend analysis and impact metrics |

### Agent layer — `src/care_pilot/agent/`
- Bounded reasoning helpers. Agents propose; they never authorize delivery or write durable state directly.
- All agents inherit `BaseAgent[InputT, OutputT]` from `agent/core/` and return `AgentResult[OutputT]`.
- Retrieved by name from `AgentRegistry`; never instantiated ad-hoc in feature code.

### Platform layer — `src/care_pilot/platform/`
- Infrastructure adapters. Feature code only touches platform through typed protocols or store interfaces.

| Sub-package | Responsibility |
|-------------|----------------|
| `persistence/` | domain SQLite repos + `SQLiteRepository` facade + typed protocols |
| `auth/` | Session signing, `SQLiteAuthStore` / `InMemoryAuthStore` |
| `cache/` | Redis + in-memory caches (profiles, snapshots, rate limits) |
| `messaging/` | Alert outbox, sink adapters (Telegram, WhatsApp, email) |
| `scheduling/` | Distributed coordination locks (Redis + in-memory), reminder scheduler |
| `observability/` | Structured logging, readiness probes, workflow contracts, tool policy registry |
| `storage/` | Media upload pipeline + ingestion hooks |

### Config layer — `src/care_pilot/config/`
- Single composition root (`app.py` → `AppSettings`).
- `get_settings()` validates cross-field constraints.

### Core layer — `src/care_pilot/core/`
- Pure primitives: IDs, base errors, domain-neutral events, clock/time helpers.
- **Contracts**: `src/care_pilot/core/contracts/api/` defines the canonical Pydantic models for the API surface, allowing features to return typed API-ready objects without depending on the `apps/` layer.
- **No I/O, no infrastructure imports.**

---

## Request lifecycle

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

## Key architectural rules

1. **Route handlers are transport-only.** Auth check → policy check → scoped deps → call use case or API orchestrator.
2. **Business logic lives in feature use cases**, not in routers, `Depends` chains, or UI glue.
3. **Domain layer is pure.** `features/*/domain/` has no I/O and no infrastructure imports.
4. **Agents are bounded helpers.** They receive typed input, return `AgentResult`, and never touch stores.
5. **Safety is deterministic.** `features/safety/domain/engine.py` runs before any LLM output is accepted.
6. **`CaseSnapshot` is the canonical read model.** New patient-facing data sources integrate through it.
7. **Platform adapters are the only I/O boundary.** Feature code does not open connections directly.
8. **Contracts break reverse dependencies.** Features return models from `core/contracts/api/` to avoid depending on the API app.

---

## Runtime model

- SQLite for durable storage (`care_pilot.db`, `care_pilot_auth.db`)
- In-memory fallbacks for cache and coordination when Redis is absent
- API and worker share the same local SQLite stores
- Chat memory and vector stores persist under `data/runtime/` and `data/vectorstore/`
- Redis for ephemeral state, distributed locks, and worker signaling in production-aligned environments.
