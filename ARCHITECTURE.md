# Architecture

## Purpose
This is the canonical architecture reference for Dietary Guardian. It describes the current modular-monolith baseline, the ownership boundaries that contributors should preserve, and the scale-later direction for the hackathon branch.

Related docs:
- `README.md`
- `SYSTEM_ROADMAP.md`
- `docs/developer-guide.md`
- `docs/operations-runbook.md`

## Current system shape
Dietary Guardian is a feature-first modular monolith with one codebase and clear ownership boundaries.

Canonical backend import surfaces:
- `src/dietary_guardian/features/` for product behavior
- `src/dietary_guardian/agent/` for bounded model-powered capabilities
- `src/dietary_guardian/platform/` for infrastructure and runtime adapters
- `src/dietary_guardian/core/` for tiny shared primitives

Legacy layered packages under `application/`, `domain/`, `infrastructure/`, and `capabilities/` have been removed. New work should only target the feature-first surfaces described below.

### Interface layer
- `apps/web` is the primary user-facing interface
- future messaging channels should integrate through the same API and workflow contracts

### API layer
- `apps/api/dietary_api` owns HTTP transport, auth, policy checks, request validation, error mapping, and request/correlation IDs
- routers stay thin and delegate behavior into services and application use cases

### Feature layer
- `src/dietary_guardian/features` owns product behavior and the obvious business entrypoints
- every feature should expose one clear `service.py` starting point
- the companion care loop stays grouped under `features/companion/`:
  - `core`
  - `personalization`
  - `engagement`
  - `care_plans`
  - `interactions`
  - `clinician_digest`
  - `impact`
- feature services may call `agent/` and `platform/`, but apps should not bypass them for business actions

### Agent layer
- `src/dietary_guardian/agent` contains bounded model/provider logic
- agents help with bounded reasoning, but they do not own durable state or bypass deterministic safety

### Platform layer
- `src/dietary_guardian/platform` owns persistence, auth, messaging, scheduling, storage, observability, and cache adapters
- app-data persistence is SQLite-first for the hackathon branch, with one store-selection path for durable local prototyping

### Core layer
- `src/dietary_guardian/core` contains tiny shared primitives only
- keep IDs, base errors, config bootstrap, clock/time helpers, and domain-neutral events here

## Core request lifecycle
1. A request enters through the web app or another client.
2. FastAPI authenticates the session, checks policy, validates input, and attaches trace metadata.
3. A feature service loads and fuses state into a `CaseSnapshot`.
4. Companion personalization and engagement modules determine focus, barriers, and support mode.
5. Agent capabilities and deterministic feature rules build the proposal payload.
6. Deterministic safety review approves, adjusts, or escalates the result.
7. Clinician digest and impact summary are produced from the same state bundle when needed.
8. Platform adapters persist durable outputs and emit follow-up work.
9. Workers continue reminders, outbox processing, and related background tasks.

## Module ownership map

```text
apps/api/dietary_api/                HTTP transport, auth, policy, response mapping
apps/web/                            Next.js routes, components, typed API clients
apps/workers/                        external worker runtime
src/dietary_guardian/features/       product behavior and business entrypoints
src/dietary_guardian/agent/          bounded model/provider logic
src/dietary_guardian/platform/       persistence and external adapters
src/dietary_guardian/core/           tiny shared primitives
```

## Key architectural rules
- Keep route handlers transport-only.
- Keep business logic in feature `service.py` entrypoints or bounded supporting modules, not in routers or UI glue.
- Keep deterministic logic as the source of truth for durable care state.
- Treat agents as bounded helpers behind typed contracts.
- Keep persistence and external integrations behind platform adapters.
- Make durable state transitions observable and testable.
- Keep safety validation injectable via `SafetyPort` — agents must not instantiate concrete safety implementations directly.

## Governing principles
- Prefer policy-governed capabilities over agent-first decomposition.
- Prefer deterministic scoring, retrieval, templates, and state machines before adding model reasoning.
- Treat typed longitudinal state and event history as the system of record, not chat memory.
- Keep safety independent from proposal generation so it can veto, downgrade, or escalate any high-impact response.
- Keep replay, traceability, and explainability as runtime requirements rather than optional observability extras.
- Keep the product culture-first and safety-always: local Singapore relevance should improve adherence, but it must never weaken the safety boundary.

## Safety and orchestration model
- Deterministic screening and policy checks run before any optional ambiguity-review agent behavior.
- Agents may propose, summarize, or enrich, but they do not authorize delivery and they do not write durable state directly.
- Every user-visible recommendation should remain traceable to the current state snapshot, evidence inputs, workflow events, and final safety decision.
- Programmatic orchestration remains the default pattern; agent-to-agent delegation should stay limited to bounded synthesis subtasks.
- The system is informational and care-support oriented, not a diagnosis or treatment authority.
- The minimum hard-escalation class includes emergency or urgent red flags such as chest pain, trouble breathing, stroke-like symptoms, severe allergic reaction signs, loss of consciousness, severe confusion, severe bleeding, and self-harm risk when in scope.
- User-visible recommendation flows should preserve structured safety outcomes such as allow, downgrade, clarification, refusal, or escalation.

## Current runtime model

### Local default
- SQLite for durable storage
- optional in-memory ephemeral services
- API and worker can share the same local app store

### Target-aligned local and production path
- SQLite for durable state during the hackathon branch
- Redis for optional ephemeral state, coordination, and worker signaling
- external worker process for reminders, outbox processing, and future async workflows when needed

## Important implemented subsystems
- companion orchestration with case snapshot, personalization, engagement, evidence, safety, clinician digest, and impact
- meal analysis with bounded perception plus deterministic canonical-food normalization
- canonical agent modules now live under `src/dietary_guardian/agent/`, while shared provider/model integration lives under `src/dietary_guardian/agent/shared/llm/`
- configuration is consolidated into focused settings modules with `src/dietary_guardian/config/` as the bootstrap surface
- recommendation flows with persisted profile and interaction context
- reminder scheduling and multi-channel delivery with worker support
- emotion inference behind application and infrastructure boundaries
- workflow traces, runtime contracts, and policy-governed tool access

## Scale-later direction
The target architecture is still a modular monolith, not an immediate distributed system. The intended next step is to harden the current boundaries rather than split the runtime prematurely.

Expected future expansion:
- stronger SQLite-first runtime boundaries with optional Redis coordination
- richer retrieval and citation infrastructure behind the existing evidence boundary
- more durable workflow state transitions when current orchestration limits become real
- additional bounded agents only where deterministic logic is not enough

The preferred order of operations is:
1. tighten contracts and capability boundaries
2. migrate behavior behind those boundaries incrementally
3. introduce heavier workflow/runtime infrastructure only when multi-day durability or human-in-the-loop semantics require it

## When to update this file
- ownership boundaries change
- a major subsystem is added or removed
- default runtime topology changes
- a new application-layer workflow becomes core to the product
