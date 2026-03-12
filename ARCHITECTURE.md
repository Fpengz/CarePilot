# Architecture

## Purpose
This is the canonical architecture reference for Dietary Guardian. It describes the current modular-monolith structure, the ownership boundaries that contributors must preserve, and the forward direction for the hackathon branch.

Related docs:
- `README.md`
- `SYSTEM_ROADMAP.md`
- `docs/agent-modules.md` — agent layer deep-dive (45 files)

---

## System shape

Dietary Guardian is a **feature-first modular monolith**: one codebase, strict layer ownership, no shared mutable globals. The legacy layered packages (`application/`, `domain/`, `infrastructure/`, `capabilities/`) have been removed. All new work targets the four canonical surfaces below.

```
src/dietary_guardian/
├── features/      product behavior and business entrypoints
├── agent/         bounded model-powered capabilities
├── platform/      infrastructure and runtime adapters
├── core/          tiny shared primitives
└── config/        settings composition root
```

---

## Layers

### Interface layer — `apps/web/`
- Next.js 14 app router; typed API clients auto-generated from FastAPI schemas.
- Future messaging channels (WhatsApp, Telegram) integrate through the same API and workflow contracts.

### API layer — `apps/api/dietary_api/`
- Owns HTTP transport, session auth, policy enforcement (`policy.py`), request validation, error mapping, and correlation IDs.
- Route handlers are transport-only: they validate, check policy, extract a scoped deps dataclass, and call a feature use-case function.
- **Never** put business logic in routers or router-level `Depends` chains.

### Worker layer — `apps/workers/`
- Independent process consuming the reminder scheduler and alert outbox.
- Uses distributed locks from `platform/scheduling/coordination/` to prevent duplicate delivery.

### Feature layer — `src/dietary_guardian/features/`
- Owns all product behavior. Each sub-package contains `domain/` (pure types + rules) and `use_cases.py` (orchestration).
- Feature code may call `agent/` and `platform/`, but `apps/` must not bypass feature use cases for business actions.

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
| `core/` | `CaseSnapshot` read model, health analytics, emotion signal models |
| `personalization/` | Preference-driven meal and lifestyle personalization |
| `engagement/` | Emotion-aware engagement, session tracking |
| `care_plans/` | Adaptive care plan generation |
| `clinician_digest/` | Clinical summary cards for practitioners |
| `impact/` | Health trend analysis and impact metrics |
| `interactions/` | Patient–companion interaction history |

### Agent layer — `src/dietary_guardian/agent/`
- Bounded reasoning helpers. Agents propose; they never authorize delivery or write durable state directly.
- All agents inherit `BaseAgent[InputT, OutputT]` from `agent/core/` and return `AgentResult[OutputT]`.
- Retrieved by name from `AgentRegistry`; never instantiated ad-hoc in feature code.

| Sub-package | Agent |
|-------------|-------|
| `runtime/` | `LLMFactory`, `LLMCapabilityRouter`, `InferenceEngine` |
| `core/` | `BaseAgent`, `AgentRegistry`, `AgentResult` envelope |
| `dietary/` | `DietaryAgent` — safety pre-screen + LLM meal reasoning |
| `meal_analysis/` | `MealAnalysisAgent` — vision perception facade |
| `recommendation/` | `RecommendationAgent` — deterministic plan synthesis |
| `emotion/` | `EmotionAgent` + HuggingFace inference infra |
| `meal_analysis/` | `HawkerVisionModule` — image → `MealPerception` |
| `chat/` | `ChatAgent`, `QueryRouter`, SSE streaming, audio, `[TRACK]` parsing |

### Platform layer — `src/dietary_guardian/platform/`
- Infrastructure adapters. Feature code only touches platform through typed protocols or store interfaces.

| Sub-package | Responsibility |
|-------------|----------------|
| `persistence/` | 7 domain SQLite repos + `SQLiteRepository` facade + typed protocols |
| `auth/` | Session signing, `SQLiteAuthStore` / `InMemoryAuthStore` |
| `cache/` | Redis + in-memory caches (profiles, snapshots, rate limits) |
| `messaging/` | Alert outbox, sink adapters (Telegram, WhatsApp, WeChat, email) |
| `scheduling/` | Distributed coordination locks (Redis + in-memory), reminder scheduler |
| `observability/` | Structured logging, readiness probes, workflow contracts, tool policy registry |
| `storage/` | Media upload pipeline + ingestion hooks |

### Config layer — `src/dietary_guardian/config/`
- Single composition root (`app.py` → `AppSettings`).
- `LLMSettings` exposes four typed `@property` frozen-dataclass views: `.gemini`, `.openai`, `.local`, `.inference`.
  Never read flat provider fields directly in agent or feature code.
- `get_settings()` validates cross-field constraints (secrets required in prod, Redis required for external workers).

### Core layer — `src/dietary_guardian/core/`
- Pure primitives: IDs, base errors, domain-neutral events, clock/time helpers, config bootstrap shims.
- **No I/O, no infrastructure imports.**

---

## Request lifecycle

```
Client
  │
  ▼
apps/api/dietary_api/  ← authenticate session, check policy, validate input
  │
  ▼
features/<feature>/use_cases.py  ← load CaseSnapshot, orchestrate domain logic
  │              │
  │              ▼
  │        features/safety/  ← deterministic safety screen (runs before any LLM output is trusted)
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

1. **Route handlers are transport-only.** Auth check → policy check → scoped deps → call use case.
2. **Business logic lives in feature use cases**, not in routers, `Depends` chains, or UI glue.
3. **Domain layer is pure.** `features/*/domain/` has no I/O and no infrastructure imports.
4. **Agents are bounded helpers.** They receive typed input, return `AgentResult`, and never touch stores.
5. **Safety is deterministic.** `features/safety/domain/engine.py` runs before any LLM output is accepted.
6. **`CaseSnapshot` is the canonical read model.** New patient-facing data sources integrate through it.
7. **Platform adapters are the only I/O boundary.** Feature code does not open connections directly.
8. **`SafetyPort` is injected.** No agent or feature module instantiates a concrete safety implementation.
9. **`LLMSettings` views are the only provider access path.** Use `.gemini`, `.openai`, `.local`, `.inference`.

---

## Governing principles

- Prefer deterministic scoring, retrieval, templates, and state machines before adding model reasoning.
- Prefer policy-governed capabilities over agent-first decomposition.
- Treat typed longitudinal state and event history as the system of record, not chat memory.
- Keep safety independent from proposal generation so it can veto, downgrade, or escalate any response.
- Keep replay, traceability, and explainability as runtime requirements, not optional observability extras.
- Keep the product culture-first and safety-always: Singapore-local relevance must never weaken the safety boundary.

---

## Safety and orchestration model

- Deterministic screening and policy checks run before any optional LLM behavior.
- Every user-visible recommendation is traceable to: current `CaseSnapshot`, evidence inputs, workflow events, and the final safety decision.
- Programmatic orchestration is the default; agent-to-agent delegation is limited to bounded synthesis subtasks.
- The system is informational and care-support oriented — not a diagnosis or treatment authority.
- Hard-escalation triggers include: chest pain, breathing difficulty, stroke signs, severe allergic reaction, loss of consciousness, severe confusion or bleeding, and self-harm risk.
- Safety outcomes preserved in recommendation flows: `allow`, `downgrade`, `clarification`, `refusal`, `escalation`.

---

## Runtime model

### Local (default)
- SQLite for durable storage (`dietary_guardian.db`, `dietary_guardian_auth.db`, `clinical_safety.db`)
- In-memory fallbacks for cache and coordination when Redis is absent
- API and worker share the same local SQLite stores
- Chat memory and vector stores persist under `data/runtime/` and `data/vectorstore/`

### Production-aligned path
- SQLite for durable state during the hackathon branch
- Redis for ephemeral state, distributed locks, and worker signaling
- External worker process for reminders, outbox, and future async workflows

---

## Implemented subsystems

| Subsystem | Location |
|-----------|----------|
| Config — LLMSettings typed views | `config/llm.py` |
| Safety engine — deterministic thresholds + drug interactions | `features/safety/domain/engine.py` |
| CaseSnapshot — canonical patient read model | `features/companion/core/` |
| Meal analysis — vision perception + food normalization | `features/meals/`, `agent/meal_analysis/` |
| Recommendations — scoring + context + orchestration | `features/recommendations/domain/` |
| Companion orchestration — personalization, engagement, clinician digest, impact | `features/companion/` |
| Reminder scheduling + multi-channel outbox | `features/reminders/`, `platform/messaging/` |
| Emotion inference | `agent/emotion/` |
| Chat pipeline — SSE streaming, audio, `[TRACK]` parsing | `agent/chat/` |
| Persistence — 7 domain SQLite repos + facade + typed protocols | `platform/persistence/` |
| Workflow traces + policy-governed tool access | `platform/observability/` |

---

## Scale-later direction

The target is still a modular monolith. The next step is to harden boundaries rather than split the runtime.

Preferred expansion order:
1. Tighten typed contracts and capability boundaries.
2. Migrate behavior behind those boundaries incrementally.
3. Introduce heavier workflow or runtime infrastructure only when multi-day durability or human-in-the-loop semantics require it.

Expected future growth areas:
- Richer retrieval and citation infrastructure behind the evidence boundary.
- More durable workflow state transitions when orchestration limits are hit.
- Additional bounded agents only where deterministic logic is insufficient.

---

## When to update this file
- Ownership boundaries change.
- A major subsystem is added or removed.
- Default runtime topology changes.
- A new application-layer workflow becomes core to the product.
