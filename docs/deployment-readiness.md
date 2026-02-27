# Deployment Readiness Checklist

## CI Hardening
- Added GitHub Actions pipeline: `.github/workflows/ci.yml`
- Backend gates:
  - `ruff check .`
  - `ty check . --extra-search-path src`
  - `pytest` with coverage gate (`--cov-fail-under=35`)
- Web gates:
  - `pnpm web:lint`
  - `pnpm web:typecheck`
  - `pnpm web:build`
  - `pnpm --dir apps/web test:e2e` (Playwright smoke)

## Container Hardening
- Added root `Dockerfile`:
  - `python:3.12-slim` base
  - non-root runtime user (`uid=10001`)
  - `/api/v1/health/live` healthcheck
  - runtime config validation prior to app start
- Added `.dockerignore` to reduce build context and exclude local artifacts.

## Runtime Config Validation
- Added `apps/api/dietary_api/runtime_validate.py`
- Enforces non-default `SESSION_SECRET` for deployment startup.

## Startup/Shutdown Lifecycle
- App lifespan hooks added in `apps/api/dietary_api/main.py`
- Graceful shutdown closes context resources via `close_app_context`.
- Lifecycle test coverage: `apps/api/tests/test_api_lifecycle.py`

## Dev Networking Contract
- Next dev origin policy is configured through `NEXT_ALLOWED_DEV_ORIGINS`.
- Browser traffic should remain same-origin through `/backend/*` proxying to `BACKEND_API_BASE_URL`.
- API CORS allowlist must include all active dev origins (localhost + LAN when applicable).
