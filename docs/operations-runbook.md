# Operations Runbook

See also:
- `docs/developer-guide.md`
- `docs/config-reference.md`

## Supported runtime profiles

### Lightweight local

```bash
uv run python scripts/dg.py dev
```

Use this for fast local development with default local backends.

### Target-aligned local

```bash
uv run python scripts/dg.py infra up
```

This is the supported production-aligned topology:
- API runtime
- web runtime
- external worker
- SQLite for durable state
- Redis for cache, coordination, and worker signaling

## Readiness and health

Endpoint:
- `GET /api/v1/health/ready`

CLI gate:

```bash
uv run python scripts/dg.py readiness http://127.0.0.1:8001
```

Strict mode:

```bash
READINESS_FAIL_ON_WARNINGS=1 uv run python scripts/dg.py readiness http://127.0.0.1:8001
```

## Validation gates

Full:

```bash
uv run python scripts/dg.py test comprehensive
```

Scoped:

```bash
uv run python scripts/dg.py test backend
uv run python scripts/dg.py test web
```

## Routine commands

Infra control:

```bash
uv run python scripts/dg.py infra status
uv run python scripts/dg.py infra logs
uv run python scripts/dg.py infra down
```

Migration:

```bash
```

## Incident triage
1. Confirm infra health if Redis-backed worker coordination is expected.
2. Run readiness and inspect failed or warning checks.
3. Verify API and worker processes are running with the intended backend settings.
4. Check reminder and notification settings if async behavior is involved.
5. Re-run scoped validation for the affected subsystem.
6. Use the comprehensive gate before closing the incident.

## Common issues

### Readiness is degraded
- provider settings are missing or invalid
- Redis is configured but unreachable

### Reminder workflows are not dispatching
- worker is not running
- scheduler-related settings or notification endpoints are missing

### Runtime policy behavior is unexpected
- enforcement mode is still `shadow`
- policy records do not match the active role, agent, or environment

## Observability
- use request ID and correlation ID for traceability
- inspect workflow traces through the workflows UI or API
- watch worker-loop failures to distinguish transient retries from process-level incidents

## Update this file when
- runtime profiles change
- readiness/operational commands change
- incident workflow changes materially
