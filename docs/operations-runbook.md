# Operations Runbook

Last updated: 2026-03-06  
See also: [`docs/developer-guide.md`](../docs/developer-guide.md), [`docs/config-reference.md`](../docs/config-reference.md), [`docs/nightly-ops.md`](../docs/nightly-ops.md)

## 1) Startup Profiles

### Lightweight Local (default)
```bash
uv run python scripts/dg.py dev
```

Use for rapid application development with local defaults.

### Target-Aligned Local (Postgres + Redis + worker)
```bash
uv run python scripts/dg.py infra up
uv run python scripts/dg.py migrate postgres
uv run python scripts/dg.py smoke postgres-redis
```

Use for validating persistence/cache/worker coordination paths.

## 2) Health and Readiness Checks

### Readiness Endpoint
- Endpoint: `GET /api/v1/health/ready`
- Expected statuses:
  - `ready`
  - `degraded`
  - `not_ready`

### CLI Readiness Gate
```bash
uv run python scripts/dg.py readiness http://127.0.0.1:8001
```

Use strict warning mode in staging/prod-like checks:
```bash
READINESS_FAIL_ON_WARNINGS=1 uv run python scripts/dg.py readiness http://127.0.0.1:8001
```

## 3) Validation Gates

### Full Validation
```bash
uv run python scripts/dg.py test comprehensive
```

### Scoped Validation
```bash
uv run python scripts/dg.py test backend
uv run python scripts/dg.py test web
```

## 4) Routine Operational Commands

### Infra Control
```bash
uv run python scripts/dg.py infra status
uv run python scripts/dg.py infra logs
uv run python scripts/dg.py infra down
```

### Migration and Keyspace Operations
```bash
uv run python scripts/dg.py migrate postgres
uv run python scripts/dg.py migrate redis-keyspace --redis-url <REDIS_URL>
uv run python scripts/dg.py migrate redis-keyspace --redis-url <REDIS_URL> --apply
```
Use the Redis keyspace migration command only for one-time import of legacy v1 keys into v2 naming.

## 5) Incident-Triage Checklist
1. Confirm Docker/infra health (if using Postgres/Redis profile).
2. Run readiness endpoint and inspect failed/warn checks.
3. Verify API and worker process status.
4. Check scheduler intervals and notification settings.
5. Re-run scoped tests for affected subsystem.
6. Escalate to full comprehensive gate before closure.

## 6) Common Operational Issues

### API starts but readiness is degraded
- Missing provider/env values.
- Redis/Postgres configured but not reachable.

### Reminder workflows not dispatching
- Scheduler disabled (`--no-scheduler` or worker not running).
- Notification endpoints/preferences missing.

### Workflow policy behavior mismatch
- Enforcement mode in `shadow` when `enforce` is expected.
- Policy records exist but do not match role/agent/tool/environment filters.

## 7) Logs and Observability
- Use correlation ID and request ID for cross-service tracing.
- Inspect workflow timelines through `/workflows` UI or workflow API routes.
- Keep readiness and smoke output artifacts for incident notes.

## When to Update This Document
- New run modes or script commands.
- Changes in readiness model or dependency checks.
- Worker/runtime behavior changes that affect operations.
