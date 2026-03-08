# TODO: Centralized Execution Plan

This file is the canonical execution backlog for the repository. It replaces the old `merge_plan.md` workflow and also replaces the temporary multi-agent packet board. Emotion Phase 1 is already merged on `agent/merge-emotion-services` at commit `1234451`; the next work is production hardening and interface stabilization, executed sequentially by the main agent.

## Baseline

- Emotion Phase 1 is already merged:
  - `/api/v1/emotions/{health,text,speech}`
  - `/emotion/{health,text,speech}`
- The codebase is a solid v1 baseline, but not production-hardened for multi-instance traffic.
- The strongest current areas are:
  - documentation discipline
  - auth/session basics
  - request correlation
  - broad backend coverage
- The highest-priority gaps are:
  - opaque API response contracts
  - broad `AppContext` service-locator usage
  - in-process workflow/timeline state
  - in-memory per-process rate limiting
  - incomplete frontend error-envelope handling
  - loose production surface hardening
  - missing full production topology validation

## Working Rules

- `todo.md` is the only canonical planning file.
- `merge_plan.md` stays retired and should not be recreated.
- Multi-agent packet execution is suspended for now.
- The main agent executes items in order unless a later item is clearly independent and blocked less.
- Any task touching high-risk shared files must run full validation before moving on.
- High-risk shared files for this plan include:
  - `apps/api/dietary_api/deps.py`
  - `src/dietary_guardian/config/settings.py`
  - `apps/api/dietary_api/policy.py`
  - `src/dietary_guardian/infrastructure/persistence/*`
  - `.github/workflows/*`

## Item 0: Branch Hygiene Recovery

- Status: `done`
- Priority: `P0`

Goal:
- Recover from contaminated branch state and re-establish `main` as the clean starting point.

Why this matters:
- The previous `fix/web-error-envelope` branch mixed Packet 1 and Packet 2 work, which invalidated packet isolation and made the multi-agent board unreliable.

In Scope:
- Return to `main`.
- Discard the contaminated working state.
- Confirm `todo.md` is the canonical planning file.

Out of Scope:
- Feature implementation.

Primary Files:
- `todo.md`

Validation:
- clean working tree on `main`
- `todo.md` exists
- `merge_plan.md` does not exist

Risk:
- Low, provided recovery happens before more work lands.

Rollback:
- If contaminated work was needed, it should have been archived before deletion.

Depends On:
- none

## Item 1: Stabilize Top 5 API Contracts

- Status: `ready`
- Priority: `P0`

Goal:
- Replace opaque `dict[str, object]` response fields with typed DTOs for:
  - meals
  - recommendations
  - reminders
  - workflows
  - suggestions

Why this matters:
- The review identified uneven API contracts as a major interface stability problem.
- Frontend reliability and generated API docs depend on this being fixed first.

In Scope:
- schema modules
- API service response mappers
- affected API tests

Out of Scope:
- `AppContext` decomposition
- rate limiting
- deployment topology
- unrelated domain refactors

Primary Files:
- `apps/api/dietary_api/schemas/models.py`
- `apps/api/dietary_api/schemas/{meals,recommendations,reminders,workflows,suggestions}.py`
- relevant modules in `apps/api/dietary_api/services/`
- relevant tests in `apps/api/tests/`

Validation:
- `uv run ruff check .`
- `uv run ty check . --extra-search-path src --output-format concise`
- `uv run pytest -q`

Risk:
- High. Contract churn can break API consumers and tests if the change is not additive and disciplined.

Rollback:
- Revert DTO migration one domain at a time if a specific surface becomes unstable.

Depends On:
- Item 0

## Item 2: Finish Frontend Error Envelope and Domain Client Migration

- Status: `ready`
- Priority: `P0`

Goal:
- Parse backend error envelopes in the web client instead of throwing raw response text.
- Continue moving request/response ownership into domain clients instead of the legacy consolidated shim.

Why this matters:
- The backend already provides structured `error.code` data, but the frontend discards it.
- Without this, frontend flows remain harder to debug and less safe to branch on.

In Scope:
- typed request error object
- domain client request/response ownership
- compatibility wrapper for legacy imports if needed

Out of Scope:
- backend API behavior changes
- proxy hardening
- login UX gating

Primary Files:
- `apps/web/lib/api.ts`
- `apps/web/lib/api/*`
- `apps/web/lib/types.ts`

Validation:
- `pnpm web:typecheck`
- relevant web tests for API client/error parsing

Risk:
- Medium. Non-envelope failures still need graceful fallback behavior.

Rollback:
- Keep a compatibility wrapper in `api.ts` if full migration is too wide for one change.

Depends On:
- Item 1 if the frontend uses newly typed DTO shapes

## Item 3: Split AppContext into Domain Dependency Providers

- Status: `ready`
- Priority: `P0`

Goal:
- Reduce broad service-locator coupling by narrowing route/service dependencies to explicit domain providers.

Why this matters:
- `AppContext` is currently acting as a broad implicit dependency bag, which weakens boundaries and increases coupling.

In Scope:
- first-wave provider split for:
  - meals
  - recommendations
  - workflows
  - emotions

Out of Scope:
- full repo-wide dependency injection rewrite
- persistence durability
- rate limiting
- frontend work

Primary Files:
- `apps/api/dietary_api/deps.py`
- `apps/api/dietary_api/routes_shared.py`
- selected route/service modules in `apps/api/dietary_api/`

Validation:
- `uv run ruff check .`
- `uv run ty check . --extra-search-path src --output-format concise`
- targeted API tests for migrated domains
- `uv run pytest -q`

Risk:
- High. This touches a coordinator-level shared file and can destabilize route/service wiring if widened.

Rollback:
- Migrate one domain at a time and keep old access paths until each domain is stable.

Depends On:
- Item 1

## Item 4: Make Workflow and Timeline State Durable

- Status: `ready`
- Priority: `P0`

Goal:
- Persist workflow timeline events and close the gap between `workflow_trace_persistence_enabled` and actual behavior.

Why this matters:
- Current replay/history semantics are node-local.
- This is a direct blocker for multi-instance correctness.

In Scope:
- durable timeline repository
- flag-driven write/read behavior
- replay/history integration
- readiness checks where needed

Out of Scope:
- full profile memory redesign
- unrelated persistence refactors
- frontend changes

Primary Files:
- `src/dietary_guardian/services/memory_services.py`
- `src/dietary_guardian/infrastructure/persistence/*`
- `apps/api/dietary_api/services/workflows.py`

Validation:
- `uv run ruff check .`
- `uv run ty check . --extra-search-path src --output-format concise`
- `uv run pytest -q`
- workflow replay and durability-oriented tests

Risk:
- High. Persistence and replay semantics are easy to get subtly wrong.

Rollback:
- Keep durable timeline behavior behind the existing flag until reads and replay are proven stable.

Depends On:
- Item 3

## Item 5: Externalize Operational Controls

- Status: `ready`
- Priority: `P0`

Goal:
- Move rate limiting and related operational controls onto shared Redis/Postgres-backed primitives.

Why this matters:
- In-memory per-process rate limiting is the clearest operational weakness in the current runtime.

In Scope:
- Redis-backed rate limiting
- compatibility with current error/retry shape
- readiness enforcement for production profiles

Out of Scope:
- workflow timeline persistence itself
- proxy allowlist work
- login UX changes

Primary Files:
- `apps/api/dietary_api/middleware.py`
- `src/dietary_guardian/config/settings.py`
- `src/dietary_guardian/infrastructure/cache/*`

Validation:
- `uv run ruff check .`
- `uv run ty check . --extra-search-path src --output-format concise`
- `uv run pytest -q`
- targeted rate-limit tests

Risk:
- High. Shared-control behavior must remain stable across dev and production profiles.

Rollback:
- Keep in-memory fallback for dev/test only while production profiles require shared backends.

Depends On:
- Item 4

## Item 6: Harden Production Surfaces

- Status: `ready`
- Priority: `P1`

Goal:
- Reduce config disclosure, restrict forwarded headers, gate demo UX by environment, and normalize login email handling.

Why this matters:
- These are low-to-medium severity individually, but together they are the main surface-hardening items from the review.

In Scope:
- `/api/v1/health/config` hardening
- proxy header allowlist
- login demo affordance gating
- email normalization in login and lockout flows

Out of Scope:
- major auth architecture changes
- DTO migration
- CI topology work

Primary Files:
- `apps/api/dietary_api/routers/health.py`
- `apps/web/app/backend/[...path]/route.ts`
- `apps/web/app/login/page.tsx`
- auth store files under `src/dietary_guardian/infrastructure/auth/`

Validation:
- `uv run ruff check .`
- `uv run ty check . --extra-search-path src --output-format concise`
- `uv run pytest -q`
- `pnpm web:typecheck`
- targeted auth/health tests

Risk:
- Medium. These are externally visible changes and should remain narrow.

Rollback:
- Land in narrow slices if needed: auth normalization, health hardening, and web surface hardening do not need to be one diff.

Depends On:
- Item 5

## Item 7: Define Production Topology and CI Validation

- Status: `ready`
- Priority: `P1`

Goal:
- Define one supported production topology:
  - API + Web + Worker + Postgres + Redis
- Add CI validation for that topology.

Why this matters:
- The current runtime direction is clear, but the deployment story is still incomplete for the stated product shape.

In Scope:
- deployment docs
- CI workflow configuration
- production-profile smoke validation

Out of Scope:
- new product behavior
- unrelated infrastructure cleanup

Primary Files:
- `.github/workflows/*`
- deployment docs
- validation scripts

Validation:
- existing CI checks
- new production-profile smoke lane

Risk:
- High. CI and deployment changes affect the whole repo and should land last.

Rollback:
- Revert CI changes independently from docs if the production-profile lane is unstable.

Depends On:
- Item 5
- ideally Item 6

## Important Interface Notes

- No public route renames are planned.
- The main public interface work in this backlog is:
  - typed API DTOs
  - typed frontend error handling
  - narrower internal dependency interfaces

## Required Test Scenarios

- API contract tests for the top 5 DTO migrations
- frontend error-envelope parsing tests
- workflow replay durability tests
- multi-instance rate-limit consistency tests
- auth normalization tests for login and lockout
- production-profile smoke tests for API + Web + Worker + Postgres + Redis

## Validation Matrix

Backend:

```bash
uv run ruff check .
uv run ty check . --extra-search-path src --output-format concise
uv run pytest -q
```

Web:

```bash
pnpm web:lint
pnpm web:typecheck
pnpm web:build
```

Full stack:

```bash
uv run python scripts/dg.py test backend
uv run python scripts/dg.py test web
uv run python scripts/dg.py test comprehensive
```
