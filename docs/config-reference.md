# Backend Config Reference (v1)

Source of truth: `src/dietary_guardian/config/settings.py`

## Auth / Session
- `SESSION_SECRET` (default: `dev-insecure-session-secret-change-me`)
- `COOKIE_SECURE` (default: `false`)
- `AUTH_PASSWORD_HASH_SCHEME` (default: `pbkdf2_sha256`)
- `AUTH_STORE_BACKEND` (default: `sqlite`) — `sqlite` or `in_memory`
- `AUTH_SQLITE_DB_PATH` (default: `dietary_guardian_auth.db`)
- `AUTH_SESSION_TTL_SECONDS` (default: `86400`)
- `AUTH_LOGIN_MAX_FAILED_ATTEMPTS` (default: `5`)
- `AUTH_LOGIN_FAILURE_WINDOW_SECONDS` (default: `300`)
- `AUTH_LOGIN_LOCKOUT_SECONDS` (default: `300`)
- `AUTH_AUDIT_EVENTS_MAX_ENTRIES` (default: `500`)

## API
- `API_HOST` (default: `127.0.0.1`)
- `API_PORT` (default: `8001`)
- `API_CORS_ORIGINS` (default: `http://localhost:3000`)

## LLM Provider
- `LLM_PROVIDER` (default: `test`) — `gemini`, `ollama`, `vllm`, `test`
- `GEMINI_API_KEY` / `GOOGLE_API_KEY`
- `GEMINI_MODEL`
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
