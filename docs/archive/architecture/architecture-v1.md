> [!WARNING]
> Historical archive only. Content may be outdated.
> Canonical docs: `README.md`, `docs/roadmap-v1.md`, `docs/feature-audit.md`, `docs/config-reference.md`.

> Historical architecture snapshot.
> Canonical architecture document: `ARCHITECTURE.md`.

# Architecture V1 (Hexagonal + Workflow Orchestration)

## Summary
Dietary Guardian v1 uses a **web-first monorepo** with thin apps (`api`, `web`) and a shared Python core package (`src/dietary_guardian`) organized into:

- `domain/` — pure business models and policies
- `application/` — use-cases, workflows, and port interfaces
- `infrastructure/` — adapters (SQLite, LLM/vision, messaging, auth/session persistence)
- `observability/` — logging, metrics, tracing helpers

This architecture is implemented incrementally. During the migration, legacy modules under `src/dietary_guardian/services` and `src/dietary_guardian/models` remain as compatibility layers while responsibilities move into the new packages.

The current release also includes an adaptive recommendation compatibility slice under `src/dietary_guardian/services/recommendation_agent_service.py`. It combines:
- persisted health profiles
- meal log history
- biomarker context
- localized meal catalog rules
- online interaction learning

This remains a service-layer implementation today, with the target long-term home in application/infrastructure packages once the hexagonal extraction converges.

## Core Design Rules
1. **Apps are thin**
   - `apps/api` handles transport/HTTP only
   - `apps/web` handles UI only
2. **Workflows, not chatbot blobs**
   - Multi-step agent behavior is modeled as explicit workflows/state transitions.
3. **Safety is first-class**
   - Pre-check and post-check safety decisions are explicit and testable.
4. **Ports and adapters**
   - Application code depends on interfaces (ports), not provider/database implementations.
5. **Event-first auditability**
   - Auth/workflow/tool/safety decisions should be recordable as structured events.

## Transitional Mapping (Current -> Target)
- `src/dietary_guardian/services/workflow_coordinator.py`
  - target: `src/dietary_guardian/application/workflows/*`
- `src/dietary_guardian/services/repository.py`
  - target: `src/dietary_guardian/infrastructure/persistence/*`
- `apps/api/dietary_api/services/*`
  - target: application use-cases + DTO mapping (routers remain thin)
- `src/dietary_guardian/services/recommendation_agent_service.py`
  - target: `src/dietary_guardian/application/recommendations/*` + persistence/catalog adapters
- `apps/api/dietary_api/auth.py`
  - now a compatibility layer re-exporting auth infrastructure classes
- `apps/api/dietary_api/routers/suggestions.py`
  - now delegates orchestration to `src/dietary_guardian/application/suggestions/use_cases.py`

## v1 Refactor Priorities
1. Auth/accounts/session persistence (SQLite-backed adapter + use-cases)
2. Meal analysis workflow and API use-case extraction
3. Suggestions flow orchestration + persistence
4. Household basics domain/application/infrastructure/API/web
5. Adaptive recommendation agent extraction from service-layer compatibility code

## Worker Boundary (v1)
The architecture prepares for a worker app (`apps/workers`) but v1 may continue to run workflows in-process unless a specific flow needs background execution. Outbox and job interfaces should be designed as ports so they can be moved later without changing application logic.

For personalization, this matters in the next phase:
- online interaction learning currently runs in-process during API requests
- offline preference refresh / catalog reindexing should move behind an explicit worker boundary
