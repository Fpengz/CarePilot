# Feature-First Modular Monolith Big-Bang Refactor

> **Status**: Implemented (March 12, 2026).  
> **Note**: This design doc is retained for rationale; the canonical reference is `ARCHITECTURE.md`.

## Goal
Perform a one-shot cutover to the feature-first modular monolith with a visible companion spine, a bounded AI layer, and a boring platform layer. Remove all legacy layered packages (`application/`, `domain/`, `infrastructure/`, `capabilities/`) with no backward compatibility.

## Target Structure
```
apps/
  api/
  web/
  workers/

src/
  core/
  features/
    companion/
      core/
      personalization/
      engagement/
      care_plans/
      interactions/
      clinician_digest/
      impact/
    meals/
    recommendations/
    reminders/
    reports/
    symptoms/
    medications/
    profiles/
    households/
    safety/
  agent/
    meal_analysis/
    recommendation/
    emotion/
    chat/
    core/
    runtime/
  platform/
    persistence/
    auth/
    messaging/
    scheduling/
    storage/
    observability/
    cache/
```

## Boundary Rules
- Allowed dependency flow: `apps -> features -> (agent | platform) -> core`.
- Apps stay transport-only; business logic lives in feature `service.py`.
- Agents provide bounded reasoning and do not write durable state directly.
- Safety is outside AI and evaluated by features before persistence.
- Platform contains infra only; no product rules.
- Core is tiny (IDs, errors, clocks/time, config primitives, neutral events).

## Migration Plan (Big-Bang)
1. Create/confirm the final directory skeleton.
2. Move feature behavior from `application/` and `domain/` into `features/` with one `service.py` per feature.
3. Move all AI to `agent/` and update imports to `dietary_guardian.agent.*`.
4. Move all infra adapters into `platform/`.
5. Update all imports across apps, web, workers, and tests.
6. Delete `application/`, `domain/`, `infrastructure/`, `capabilities/`.

## Testing
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run ruff check .`
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run ty check . --extra-search-path src --output-format concise`
- `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q`
- `pnpm web:lint`
- `pnpm web:typecheck`
- `pnpm web:build`
