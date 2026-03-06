# Product Roadmap

## Purpose
This roadmap aligns the current repository with the target production platform:
- FastAPI backend
- Next.js frontend
- PostgreSQL + Redis production data plane
- LLM-driven orchestration
- RAG-based retrieval
- multi-agent workflow execution

It is explicit about current maturity so contributors can distinguish:
- what is already implemented
- what is being actively hardened
- what remains a research or platform investment

Latest capability verification is tracked in `docs/feature-audit.md`.

## Current Maturity Snapshot
Current implemented baseline:
- FastAPI + Next.js monorepo with typed API and web contracts
- SQLite-backed auth and application persistence
- PostgreSQL-backed app, auth, and household store adapters with SQLite fallback
- Redis-backed cache and coordination adapters with worker signal waiting and lock-based coordination
- action-based authorization and centralized error semantics
- in-process workflow coordination with structured timeline events
- adaptive meal recommendation with online interaction learning
- reminder scheduling and multi-channel delivery with durable logs
- dedicated account settings surface with health-profile editing moved out of the dashboard
- guided health-profile onboarding in Settings with persisted progress
- daily nutrition summary and remaining-target tracking on the meals surface
- cautious nutrition-pattern inference from meal history and preferences
- read-only caregiver monitoring within the active household
- opt-in periodic mobility reminders built on the reminder scheduling stack
- report parsing with symptom-summary context and workflow timeline visibility
- local compose/dev scaffolding for PostgreSQL, Redis, and external workers
- unified scripts CLI (`uv run python scripts/dg.py`) with comprehensive validation orchestration
- workflow governance admin surface for runtime contract snapshots and tool policy inspection/actions (`/workflows`)
- smoke-tested primary web journeys

Current maturity gaps relative to the target platform:
- daemon-backed PostgreSQL and Redis validation still depends on the local/dev infra stack rather than CI-hosted integration coverage
- production hardening for pooling, observability, and failure injection is still early
- RAG ingestion, indexing, retrieval, and citation layers are not yet first-class production modules
- agent routing is still partly implemented through service-layer orchestration rather than a dedicated registry/runtime
- offline evaluation, retrieval benchmarking, and research-grade safety evaluation are still early

## Feature Matrix (Canonical)
| Feature | Status | Current Surface / Contract |
|---|---|---|
| Health profile gradual guidance (interactive Q&A) | `**[Complete]**` | `/settings` guided onboarding + advanced edit (`/api/v1/profile/health/onboarding*`) |
| Nutritional deficiency inference from meal preferences | `**[Complete]**` | Daily summary insights + pattern flags (`/api/v1/meal/daily-summary`) |
| Meal intake tracking with real-time updates | `**[Complete]**` | Meal logging, daily remaining targets, weekly rollups (`/api/v1/meal/analyze`, `/api/v1/meal/daily-summary`, `/api/v1/meal/weekly-summary`) |
| Community-based caregiving support | `**[Complete]**` | Household read-only care monitoring (`/household`, `/api/v1/households/care/*`) |
| Environmental monitoring (air quality / conditions) | `**[Research]**` | Not productized yet; tracked as research item |
| Demographic context awareness (fairness/privacy constrained) | `**[Research]**` | Not productized yet; tracked as research item |
| Periodic mobility reminders | `**[Complete]**` | Mobility settings + reminder generation/delivery (`/settings`, `/reminders`, `/api/v1/reminders/mobility-settings`) |
| Medication tracking + adherence metrics | `**[Complete]**` | Regimen CRUD + adherence events/metrics (`/medications`, `/api/v1/medications/*`) |
| Symptom check-ins | `**[Complete]**` | Symptom logging/list/summary plus report-context synthesis (`/symptoms`, `/reports`, `/api/v1/symptoms/*`, `/api/v1/reports/parse`) |
| Patient to doctor clinical card generation | `**[Complete]**` | Clinical card generation/list/detail (`/clinical-cards`, `/api/v1/clinical-cards/*`) |
| Numerical data change analysis | `**[Complete]**` | Deterministic trend/delta endpoints (`/metrics`, `/api/v1/metrics/trends`) |

## Goal Labels
- `Research Goal` — experimental or model-quality work
- `Engineering Goal` — application, workflow, API, and product-delivery work
- `Infrastructure Goal` — runtime, deployment, scale, resilience, and observability work

## Status Labels
- `**[Complete]**` Delivered and validated in the repository
- `**[In Progress]**` Active implementation or immediate hardening target
- `**[Planned]**` Approved backlog item
- `**[Research]**` Requires experimentation before production commitment

## Short-Term (0–3 Months)

### 1. Core Infrastructure
- `**[Complete]**` PostgreSQL-ready persistence boundary
  - `Engineering Goal`, `Infrastructure Goal`
  - Runtime backend selection, schema bootstrap, and concrete PostgreSQL app/auth/household adapters are now implemented with SQLite fallback retained.
  - Exit criteria:
    - application repositories have working PostgreSQL-backed implementations
    - auth and household stores run on PostgreSQL
    - schema groups are bootstrapped for auth, health, meals, reminders, and workflow state
    - migration/bootstrap path is runnable for PostgreSQL-backed environments

- `**[Complete]**` Redis-backed async and ephemeral state layer
  - `Infrastructure Goal`
  - Redis cache and coordination adapters now back worker wakeups, lock-based scheduler/outbox coordination, and short-lived runtime state, with polling fallback retained.
  - Exit criteria:
    - queue/caching responsibilities are explicitly separated from durable storage
    - workers can block on Redis signals and fall back to polling safely
    - reminder and workflow side effects can run through Redis-backed workers without API coupling

- `**[Complete]**` Explicit agent registry and workflow runtime contract
  - `Engineering Goal`
  - Named runtime registry and workflow runtime-contract read surface are implemented for auditable orchestration metadata.
  - Exit criteria:
    - agents declare capabilities, allowed tools, and output contracts
    - workflow runtime contracts are exposed via workflow API read endpoints

- `**[Complete]**` Logging, correlation, and error normalization foundation
  - `Infrastructure Goal`
  - Structured logging, correlation IDs, centralized errors, and workflow timeline capture are already in place.

### 2. AI/ML Components
- `**[In Progress]**` Recommendation-agent hardening and offline refresh hooks
  - `Research Goal`, `Engineering Goal`
  - Extend the current online reranking system with offline refresh and richer diagnostics.
  - Exit criteria:
    - preference snapshot rebuild job exists
    - ranking deltas are explainable after refreshes

- `**[Planned]**` Prompt orchestration standardization
  - `Engineering Goal`
  - Centralize prompt assembly, model selection, and output validation patterns across agents.
  - Exit criteria:
    - prompt construction is no longer scattered across service code
    - agent contracts define prompt inputs and output schemas explicitly

- `**[Research]**` RAG v1 foundation
  - `Research Goal`, `Engineering Goal`
  - Establish ingestion, chunking, embedding, retrieval, and citation packaging boundaries for trusted medical and nutritional sources.
  - Exit criteria:
    - source provenance model defined
    - retrieval service contract defined
    - offline retrieval evaluation set identified

- `**[Planned]**` Safety and guardrail coverage expansion
  - `Research Goal`, `Engineering Goal`
  - Extend safety beyond current recommendation and reminder semantics into retrieval and broader multi-agent outputs.

### 3. Product Features
- `**[Complete]**` User state tracking and personalization baseline
  - `Engineering Goal`
  - Persisted health profiles, household context, meal history, and recommendation interactions are implemented.

- `**[Complete]**` Settings-first health profile management and cleaner dashboard
  - `Engineering Goal`
  - Account settings now own health-profile editing, while the dashboard has been reduced to a summary-oriented surface.

- `**[Complete]**` Daily intake tracking and cautious nutrition-pattern guidance
  - `Engineering Goal`, `Research Goal`
  - The product now computes daily consumed/remaining nutrition targets and emits non-diagnostic meal-pattern insights such as low protein, low fiber, high sodium, high sugar, and repetitive intake.

- `**[Complete]**` Opt-in mobility reminder workflow
  - `Engineering Goal`
  - Users can configure periodic mobility reminders, and those reminders reuse the reminder generation, notification preference, and delivery infrastructure.

- `**[Complete]**` Guided health profile Q&A onboarding
  - `Engineering Goal`
  - Settings now provide a progressive guided flow with persisted onboarding progress and advanced-edit fallback.

- `**[Complete]**` Community and caregiver support phase 2
  - `Engineering Goal`
  - The current household baseline now includes read-only caregiver-safe monitoring for household members, including profile completeness, meal summaries, insights, and reminders.

- `**[Research]**` Environmental monitoring for recommendation context
  - `Research Goal`, `Engineering Goal`
  - Evaluate air quality, temperature, and humidity inputs as recommendation context signals before productizing them.

- `**[Research]**` Demographic-context personalization with fairness controls
  - `Research Goal`, `Engineering Goal`
  - Explore whether any demographic context can be incorporated safely, fairly, and with explicit privacy/policy controls.

- `**[Planned]**` Knowledge retrieval agent
  - `Research Goal`, `Engineering Goal`
  - Add a first-class knowledge retrieval path that can support evidence-backed user guidance.

- `**[Research]**` Emotional support and escalation agent
  - `Research Goal`
  - Explore bounded emotional-state classification, safe language generation, and escalation rules.

- `**[Complete]**` Reminder automation and multi-channel scheduling baseline
  - `Engineering Goal`
  - Durable preferences, endpoints, schedules, logs, and reminder delivery adapters are implemented.

### 4. Deployment and Scaling
- `**[Complete]**` API container baseline
  - `Infrastructure Goal`
  - A production-style Dockerfile and CI validation pipeline already exist.

- `**[Complete]**` Environment profiles and secret hygiene
  - `Infrastructure Goal`
  - Explicit environment profiles (`dev`, `staging`, `prod`) and profile-aware readiness strictness are implemented with documented runtime toggles.

- `**[Complete]**` Readiness and dependency diagnostics
  - `Infrastructure Goal`
  - Health readiness now returns structured diagnostics for providers, persistence, ephemeral backends, and channel configuration with scriptable CI gating.

## Mid-Term (3–9 Months)

### 1. Core Infrastructure
- `**[Planned]**` Multi-process worker topology
  - `Infrastructure Goal`
  - Introduce dedicated worker processes for notifications, retrieval ingestion, offline learning refresh, and heavy orchestration tasks.

- `**[Planned]**` Event bus and workflow durability improvements
  - `Engineering Goal`, `Infrastructure Goal`
  - Move from in-process workflow sequencing toward durable workflow state transitions and replayable event streams.

- `**[Planned]**` Agent capability routing
  - `Engineering Goal`
  - Add a capability-driven router so workflows can resolve the correct agent set by task rather than by direct service composition.

### 2. AI/ML Components
- `**[Planned]**` RAG productionization
  - `Research Goal`, `Engineering Goal`
  - Complete retrieval indexing, ranking, citation rendering, and source trust controls.

- `**[Planned]**` Memory hierarchy
  - `Research Goal`, `Engineering Goal`
  - Separate short-term session memory, durable user memory, and retrieval-backed knowledge memory.

- `**[Research]**` Evaluation framework and prompt regression platform
  - `Research Goal`, `Infrastructure Goal`
  - Add offline datasets, prompt snapshots, task metrics, and benchmark dashboards.

### 3. Product Features
- `**[Planned]**` Chronic condition monitoring workflows
  - `Engineering Goal`, `Research Goal`
  - Add condition-aware alerting, longitudinal trend views, and policy-controlled recommendations.

- `**[Planned]**` Knowledge-grounded assistant experiences
  - `Engineering Goal`
  - Surface retrieval-backed answers and explanation cards in the web product.

- `**[Planned]**` Personalization maturity phase 2
  - `Engineering Goal`, `Research Goal`
  - Improve adherence-aware coaching, meal substitution quality, and habit-loop modeling.

### 4. Deployment and Scaling
- `**[Planned]**` Horizontal scale readiness
  - `Infrastructure Goal`
  - Add Redis-backed coordination, stateless API assumptions, and load-balancer-safe session behavior.

- `**[Planned]**` Monitoring stack expansion
  - `Infrastructure Goal`
  - Add metrics, tracing, alerting thresholds, and operator dashboards for workflow and provider health.

- `**[Planned]**` Cache strategy formalization
  - `Infrastructure Goal`
  - Define cache boundaries for retrieval, session-adjacent state, and read-heavy product surfaces.

## Long-Term (9–18 Months)

### 1. Core Infrastructure
- `**[Planned]**` Full production data plane on PostgreSQL + Redis
  - `Infrastructure Goal`
  - Retire SQLite from primary production responsibility and make PostgreSQL + Redis the supported runtime standard.

- `**[Planned]**` Durable multi-agent execution engine
  - `Engineering Goal`, `Infrastructure Goal`
  - Support resilient long-running workflows, replay, compensation, and multi-agent concurrency.

### 2. AI/ML Components
- `**[Research]**` Agent ensemble optimization
  - `Research Goal`
  - Experiment with routing strategies, model specialization, and confidence-aware fallback chains.

- `**[Research]**` Human-in-the-loop evaluation and safety review tooling
  - `Research Goal`, `Infrastructure Goal`
  - Add review queues, adjudication surfaces, and dataset capture for agent behavior quality.

- `**[Planned]**` Retrieval-aware safety and evidence scoring
  - `Research Goal`, `Engineering Goal`
  - Make citation quality and source trust first-class factors in agent outputs.

### 3. Product Features
- `**[Planned]**` Cross-channel conversational product surface
  - `Engineering Goal`
  - Support coherent user journeys across web, Telegram, WhatsApp, and WeChat with shared memory and workflow state.

- `**[Research]**` Emotional support escalation framework
  - `Research Goal`
  - Introduce clinically safe escalation patterns, crisis boundaries, and operator controls where product policy allows.

- `**[Planned]**` Advanced personalization and chronic-care programs
  - `Engineering Goal`, `Research Goal`
  - Move from isolated recommendations toward longitudinal coaching programs and condition-specific workflows.

### 4. Deployment and Scaling
- `**[Planned]**` Fault-tolerant multi-region or multi-zone runtime posture
  - `Infrastructure Goal`
  - Add stronger recovery guarantees for queues, workers, and durable event processing.

- `**[Planned]**` Policy-driven feature rollout and experimentation
  - `Infrastructure Goal`, `Engineering Goal`
  - Add environment-aware feature flags and controlled rollout paths for new agents and tools.

- `**[Planned]**` Advanced configuration telemetry and auditability
  - `Infrastructure Goal`
  - Make runtime configuration provenance and effective values observable with redaction by default.
