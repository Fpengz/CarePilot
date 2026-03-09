# Developer Guide

See also:
- `CONTRIBUTING.md`
- `ARCHITECTURE.md`
- `docs/config-reference.md`

## Setup

Requirements:
- Python 3.12+
- Node.js 20+
- `uv`
- `pnpm`
- Docker for optional Redis-backed worker smoke paths

Install:

```bash
uv sync
pnpm install
cp .env.example .env
```

## Run locally

Default local stack:

```bash
uv run python scripts/dg.py dev
```

Useful variants:

```bash
uv run python scripts/dg.py dev --no-web
uv run python scripts/dg.py dev --no-api
uv run python scripts/dg.py dev --no-scheduler
```

Target-aligned local stack:

```bash
uv run python scripts/dg.py infra up
```

## Repository map
- `apps/api/dietary_api/`: FastAPI app, routers, API services, schemas
- `apps/web/`: Next.js app, components, typed API clients, e2e coverage
- `apps/workers/`: external worker runtime
- `src/dietary_guardian/domain/`: typed domain contracts
- `src/dietary_guardian/application/`: use cases, policies, orchestration, ports
- `src/dietary_guardian/infrastructure/`: persistence and external adapters
- `src/dietary_guardian/agents/`: bounded model/provider logic
- `src/dietary_guardian/services/`: reusable domain services and workflow helpers
- `tests/` and `apps/api/tests/`: repository and API tests

## Extension patterns

### Add or change an API feature
1. Update schema contracts in `apps/api/dietary_api/schemas/` if the API shape changes.
2. Implement request handling in `apps/api/dietary_api/services/<feature>.py`.
3. Keep the route in `apps/api/dietary_api/routers/<feature>.py` transport-only.
4. Add or update API tests in `apps/api/tests/`.
5. Update typed web client code in `apps/web/lib/api/` and UI consumers in `apps/web/app/`.

### Add or change core behavior
1. Prefer `src/dietary_guardian/application/` for new use cases and orchestration.
2. Extend `src/dietary_guardian/domain/` contracts before wiring infrastructure.
3. Add infrastructure adapters under `src/dietary_guardian/infrastructure/` only after the port or contract is clear.
4. Keep agents behind typed contracts and out of durable-state ownership.

### Add or change persistence/runtime infrastructure
1. Update backend-neutral contracts when the app layer should not know the backend.
2. Implement SQLite behavior in infrastructure persistence and keep external services optional.
3. Wire backend selection through the existing builder/dependency path.
4. Extend scripts and readiness behavior only when the operational path changes.

## Testing workflow

Recommended full gate:

```bash
uv run python scripts/dg.py test comprehensive
```

Focused gates:

```bash
uv run python scripts/dg.py test backend
uv run python scripts/dg.py test web
```

Direct gates:

```bash
uv run ruff check .
uv run ty check . --extra-search-path src --output-format concise
uv run pytest -q
pnpm web:lint
pnpm web:typecheck
pnpm web:build
```

## Debugging workflow
1. Check readiness and environment configuration.
2. Run the narrowest affected backend or web tests first.
3. Confirm worker/runtime assumptions if the feature depends on reminders or async processing.
4. Escalate to the comprehensive gate before finalizing a cross-cutting change.

## Update this file when
- setup or local runtime commands change
- extension patterns change
- validation gates change materially
