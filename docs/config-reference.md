# Backend Config Reference

Source of truth: `src/dietary_guardian/config/settings.py`

Related guides:
- developer setup and extension: `docs/developer-guide.md`
- runtime operations and incident workflow: `docs/operations-runbook.md`

Environment loading conventions:
- Default source of truth is root `.env`.
- Web commands (`pnpm web:*`) load root `.env` first, then optional `apps/web/.env` overrides.

## Auth / Session
- `API_SQLITE_DB_PATH` (default: `dietary_guardian_api.db`) — application data / household persistence
- `APP_ENV` (default: `dev`) — runtime profile (`dev`, `staging`, `prod`)
- `SESSION_SECRET` (default: `dev-insecure-session-secret-change-me`)
- `COOKIE_SECURE` (default: `false`)
- `AUTH_PASSWORD_HASH_SCHEME` (default: `pbkdf2_sha256`)
- `AUTH_STORE_BACKEND` (default: `sqlite`) — `sqlite` or `in_memory`
- `AUTH_SQLITE_DB_PATH` (default: `dietary_guardian_auth.db`)
- `APP_DATA_BACKEND` (default: `sqlite`) — `sqlite` or `postgres`
- `HOUSEHOLD_STORE_BACKEND` (default: `sqlite`) — `sqlite` or `postgres`
- `POSTGRES_DSN` (required when any backend is `postgres`)
- `POSTGRES_POOL_MIN_SIZE` (default: `1`)
- `POSTGRES_POOL_MAX_SIZE` (default: `5`)
- `POSTGRES_STATEMENT_TIMEOUT_MS` (default: `5000`)
- `EPHEMERAL_STATE_BACKEND` (default: `in_memory`) — `in_memory` or `redis`
- `REDIS_URL` (required when `EPHEMERAL_STATE_BACKEND=redis`)
- `REDIS_NAMESPACE` (default: `dietary_guardian`)
- `REDIS_DEFAULT_TTL_SECONDS` (default: `300`)
- `REDIS_LOCK_TTL_SECONDS` (default: `30`)
- `REDIS_WORKER_SIGNAL_CHANNEL` (default: `workers.ready`)
- `REDIS_KEYSPACE_VERSION` (default: `v2`) — fixed to `v2` key naming mode for Redis cache/coordination stores
- `READINESS_FAIL_ON_WARNINGS` (default: profile-derived; `false` in `dev`, `true` in `staging`/`prod`)
- `REQUIRED_PROVIDER` (optional) — expected provider (`gemini`, `openai`, `ollama`, `vllm`, `test`) for readiness checks
- `AUTH_SESSION_TTL_SECONDS` (default: `86400`)
- `AUTH_LOGIN_MAX_FAILED_ATTEMPTS` (default: `5`)
- `AUTH_LOGIN_FAILURE_WINDOW_SECONDS` (default: `300`)
- `AUTH_LOGIN_LOCKOUT_SECONDS` (default: `300`)
- `AUTH_AUDIT_EVENTS_MAX_ENTRIES` (default: `500`)
- `TOOL_POLICY_ENFORCEMENT_MODE` (default: `shadow`) — `shadow` or `enforce`
- `WORKFLOW_CONTRACT_BOOTSTRAP` (default: `true`) — create/refresh startup runtime-contract snapshots

## API
- `API_HOST` (default: `127.0.0.1`)
- `API_PORT` (default: `8001`)
- `API_CORS_ORIGINS` (default: `http://localhost:3000`)
- `API_DEV_LOG_VERBOSE` (default: `false`)
- `API_DEV_LOG_HEADERS` (default: `false`)
- `API_DEV_LOG_RESPONSE_HEADERS` (default: `false`)

## Web Runtime
- `NEXT_PUBLIC_API_BASE_URL` (default: `/backend`)
- `BACKEND_API_BASE_URL` (default: `http://127.0.0.1:8001`)
- `NEXT_ALLOWED_DEV_ORIGINS` (default: `http://localhost:3000,http://127.0.0.1:3000`)
- `NEXT_PUBLIC_MEAL_ANALYZE_PROVIDER` (default: `test`)
- `NEXT_PUBLIC_DEV_LOG_FRONTEND` (default: `false`)
- `NEXT_PUBLIC_DEV_LOG_FRONTEND_VERBOSE` (default: `false`)

## LLM Provider
- `LLM_PROVIDER` (default: `test`) — `gemini`, `openai`, `ollama`, `vllm`, `test`
- `GEMINI_API_KEY` / `GOOGLE_API_KEY`
- `GEMINI_MODEL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `OPENAI_REQUEST_TIMEOUT_SECONDS`
- `OPENAI_TRANSPORT_MAX_RETRIES`
- `LOCAL_LLM_BASE_URL` / `OLLAMA_BASE_URL`
- `LOCAL_LLM_API_KEY`
- `LOCAL_LLM_MODEL`
- `LOCAL_LLM_REQUEST_TIMEOUT_SECONDS`
- `LOCAL_LLM_TRANSPORT_MAX_RETRIES`

## Image Processing
- `IMAGE_DOWNSCALE_ENABLED` (default: `false`)
- `IMAGE_MAX_SIDE_PX` (default: `1024`)

## Notifications (Telegram)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_DEV_MODE` (default: `true`)
- `TELEGRAM_REQUEST_TIMEOUT_SECONDS` (default: `10`)

## Notifications (Email / SMS / Reminder Scheduler)
- `EMAIL_DEV_MODE` (default: `true`)
- `EMAIL_SMTP_HOST`
- `EMAIL_SMTP_PORT` (default: `587`)
- `EMAIL_SMTP_USERNAME`
- `EMAIL_SMTP_PASSWORD`
- `EMAIL_SMTP_USE_TLS` (default: `true`)
- `EMAIL_FROM_ADDRESS` (default: `noreply@dietary-guardian.local`)
- `SMS_DEV_MODE` (default: `true`)
- `SMS_WEBHOOK_URL`
- `SMS_API_KEY`
- `SMS_SENDER_ID` (default: `DietaryGuardian`)
- `REMINDER_SCHEDULER_INTERVAL_SECONDS` (default: `30`)
- `REMINDER_SCHEDULER_BATCH_SIZE` (default: `100`)

## Readiness Diagnostics
- Endpoint: `GET /api/v1/health/ready`
- Status values:
  - `ready`: required checks passed and no warnings
  - `degraded`: required checks passed with warnings
  - `not_ready`: required check failure (or warning treated as failure when strict mode is enabled)
- Script gate:
  - `uv run python scripts/dg.py readiness [base_url]`
  - Set `READINESS_FAIL_ON_WARNINGS=1` to fail the script on `degraded`.

## Unified CLI Operations
- Comprehensive validation gate: `uv run python scripts/dg.py test comprehensive`
- Backend-only validation gate: `uv run python scripts/dg.py test backend`
- Web-only validation gate: `uv run python scripts/dg.py test web`
- Redis keyspace migration dry run (legacy pre-cutover data only): `uv run python scripts/dg.py migrate redis-keyspace --redis-url <REDIS_URL>`
