# Developer Guide

Last updated: 2026-03-06  
See also: [`docs/config-reference.md`](../docs/config-reference.md), [`CONTRIBUTING.md`](../CONTRIBUTING.md)

## 1) Development Environment Setup

### Prerequisites
- Python 3.12+
- Node.js 20+
- `uv`
- `pnpm`
- Docker (recommended for Postgres/Redis smoke)

### Install Dependencies
```bash
uv sync
pnpm install
```

### Configure Environment
```bash
cp .env.example .env
```

Use `docs/config-reference.md` for all runtime variables and defaults.

## 2) Run the System Locally

### Standard Dev
```bash
uv run python scripts/dg.py dev
```

Optional:
```bash
uv run python scripts/dg.py dev --no-web
uv run python scripts/dg.py dev --no-api
uv run python scripts/dg.py dev --no-scheduler
```

### Target-Aligned Local Stack (Postgres + Redis + worker)
```bash
uv run python scripts/dg.py infra up
uv run python scripts/dg.py migrate postgres
uv run python scripts/dg.py smoke postgres-redis
```

### Useful Health/Readiness Checks
```bash
uv run python scripts/dg.py readiness http://127.0.0.1:8001
uv run python scripts/dg.py infra status
uv run python scripts/dg.py infra logs
```

## 3) Extend the System

### Add a New API Feature
1. Add or update schema contracts in `apps/api/dietary_api/schemas/` (domain module + shared model updates).
2. Implement service logic in `apps/api/dietary_api/services/<feature>.py`.
3. Map route handler in `apps/api/dietary_api/routers/<feature>.py`.
4. Register routes if needed in router composition.
5. Add API tests in `apps/api/tests/`.
6. Add/extend frontend API client/types in `apps/web/lib/api/*.ts` domain modules and `apps/web/lib/types.ts`.
   - `apps/web/lib/api.ts` is compatibility-only during the migration window and should not be used for new imports.
7. Add UI route/component usage under `apps/web/app/*`.

### Add or Extend an Agent/Workflow
1. Define typed model contracts in `src/dietary_guardian/models/`.
2. Implement or extend agent logic in `src/dietary_guardian/agents/`.
3. Wire orchestration in workflow/services layer.
4. Register tools and policy constraints via tool registry/policy services.
5. Add workflow/API tests for expected timeline and policy behavior.

### Add Persistence or Runtime Infrastructure
1. Define schema updates in persistence schema modules.
2. Implement adapter methods in SQLite/Postgres stores.
3. Wire backend selection in settings/dependency context.
4. Add migration or script support in `scripts/dg.py` subcommands where needed.

## 4) Testing Workflow

### Recommended Full Gate
```bash
uv run python scripts/dg.py test comprehensive
```

### Focused Gates
```bash
uv run python scripts/dg.py test backend
uv run python scripts/dg.py test web
```

### Test Locations
- API tests: `apps/api/tests/`
- Core/unit tests: `tests/`
- Web e2e: `apps/web/e2e/`

## 5) Debugging Workflow

### Common Failure Surfaces
- Auth/session and scope mismatch.
- Provider/env misconfiguration.
- Postgres/Redis availability in target-aligned flows.
- Worker scheduler not running when reminder workflows are expected.
- Tool policy mode differences (`shadow` vs `enforce`).

### Practical Debug Sequence
1. Check env and readiness endpoint.
2. Run backend tests for affected feature.
3. Run web typecheck/build for UI/API integration.
4. Run e2e for impacted user flow.
5. Run comprehensive gate before finalizing changes.

## 6) Coding and Contribution Expectations
- Keep route handlers thin.
- Keep response/request contracts strongly typed.
- Favor service-layer orchestration over router-level business logic.
- Preserve backward compatibility unless explicitly planned.
- Include tests for every behavior change.

## When to Update This Document
- CLI command changes or new operational paths.
- New extension pattern (agent/workflow/persistence).
- Test gate changes or debug runbook changes.
