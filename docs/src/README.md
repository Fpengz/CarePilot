# `src/dietary_guardian` — Module Reference Index

Comprehensive documentation for all 268 Python modules across the `dietary_guardian` package.

Each document was generated from a full read of every source file.

---

## Documents

| File | Covers | Lines |
|------|--------|-------|
| [config-core-shared.md](./config-core-shared.md) | `config/`, `core/`, `shared/`, top-level package files | 973 |
| [platform-persistence-scheduling.md](./platform-persistence-scheduling.md) | `platform/persistence/` (all 16 repository files + food/evidence/household stores), `platform/scheduling/` | 1089 |
| [platform-auth-cache-messaging-observability.md](./platform-auth-cache-messaging-observability.md) | `platform/auth/`, `platform/cache/`, `platform/messaging/`, `platform/observability/`, `platform/storage/` | 579 |
| [features-meals-profiles-medications-symptoms.md](./features-meals-profiles-medications-symptoms.md) | `features/meals/`, `features/profiles/`, `features/medications/`, `features/symptoms/` | 781 |
| [features-safety-reminders-reports-households-recommendations.md](./features-safety-reminders-reports-households-recommendations.md) | `features/safety/`, `features/reminders/`, `features/reports/`, `features/households/`, `features/recommendations/` | 739 |
| [features-companion.md](./features-companion.md) | `features/companion/` (core, care_plans, clinician_digest, engagement, impact, personalization) | 676 |
| [../agent-modules.md](../agent-modules.md) | `agent/` — all 45 agent modules across shared, dietary, meal_analysis, recommendation, emotion, vision, chat | 435 |

**Total documented: ~5300 lines across 7 files**

---

## Architecture summary

```
src/dietary_guardian/
│
├── config/          Settings composition (AppSettings, LLMSettings with typed property views)
├── core/            Pure primitives: errors, events, ids, types, contracts
├── shared/          Timezone utilities
│
├── agent/           LLM agent layer (documented in ../agent-modules.md)
│   ├── shared/      BaseAgent, InferenceEngine, LLMFactory, LLMCapabilityRouter
│   ├── dietary/     DietaryAgent — safety + LLM meal reasoning
│   ├── meal_analysis/ MealAnalysisAgent — vision perception facade
│   ├── recommendation/ RecommendationAgent — deterministic plan synthesis
│   ├── emotion/     EmotionAgent + full HuggingFace inference infra
│   ├── vision/      HawkerVisionModule — image → MealPerception
│   └── chat/        SEA-LION conversational assistant (ChatAgent, QueryRouter, routes)
│
├── features/        Business logic organized by domain
│   ├── meals/       Meal recognition, nutrition, daily/weekly summaries
│   ├── profiles/    User health profiles, onboarding, role/social tools
│   ├── medications/ Medication regimen scheduling, mobility reminders
│   ├── symptoms/    Symptom check-in use cases
│   ├── safety/      Deterministic safety engine, drug interactions, triage
│   ├── reminders/   Reminder scheduling, notification materialization, outbox
│   ├── reports/     Biomarker PDF parsing
│   ├── households/  Multi-user household access policies
│   ├── recommendations/ Daily recommendation engine (scoring + context + orchestration)
│   └── companion/   Patient engagement orchestration
│       ├── core/    CaseSnapshot, health analytics, emotion models
│       ├── care_plans/ Adaptive care plan generation
│       ├── clinician_digest/ Clinical summary cards
│       ├── engagement/ Emotion-aware engagement, session tracking
│       ├── impact/  Health trend analysis, impact metrics
│       └── personalization/ Preference-driven meal/lifestyle personalization
│
└── platform/        Infrastructure adapters
    ├── auth/        Session signing, SQLite/in-memory auth stores
    ├── cache/       Redis + in-memory caches (profiles, snapshots, rate limits)
    ├── messaging/   Alert outbox, delivery channels (Telegram, WhatsApp, WeChat)
    ├── observability/ Logging, readiness, workflow contracts, tool policy registry
    ├── persistence/ 7 domain SQLite repos + facade + typed protocols + food/evidence stores
    ├── scheduling/  Distributed coordination locks (Redis + in-memory), reminder scheduler
    └── storage/     Media upload + ingestion pipeline
```

---

## Key architectural rules

1. **Domain layer is pure** — `features/*/domain/` has no I/O, no infrastructure imports.
2. **Application layer** (`features/*/use_cases.py`) imports from domain + platform; never from `apps/`.
3. **Routers** (`apps/api/`) import from `features/*/` only via `use_cases` or `deps`.
4. **Agents propose; they never write durable state.** All persistence goes through stores.
5. **Safety is deterministic** — `features/safety/domain/engine.py` runs threshold checks before any LLM output is trusted.
6. **`CaseSnapshot`** (`features/companion/core/snapshot.py`) is the canonical read model aggregating patient state for personalization and engagement.
7. **`LLMSettings`** exposes four typed `@property` views: `gemini`, `openai`, `local`, `inference` — never read flat fields directly in agent code.
