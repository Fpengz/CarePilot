from __future__ import annotations

from typing import TypedDict

from dietary_guardian.config.settings import Settings


class ReadinessCheck(TypedDict):
    name: str
    status: str
    required: bool
    detail: str


class ReadinessReport(TypedDict):
    status: str
    checks: list[ReadinessCheck]
    warnings: list[str]
    errors: list[str]


def _check(name: str, *, status: str, required: bool, detail: str) -> ReadinessCheck:
    return {
        "name": name,
        "status": status,
        "required": required,
        "detail": detail,
    }


def _try_redis_ping(redis_url: str) -> tuple[bool, str]:
    try:
        import redis
    except ModuleNotFoundError:
        return (False, "redis package is not installed")
    try:
        client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
        try:
            client.ping()
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()
        return (True, "redis ping succeeded")
    except Exception as exc:  # noqa: BLE001
        return (False, f"redis ping failed: {exc}")


def build_readiness_report(*, settings: Settings) -> ReadinessReport:
    checks: list[ReadinessCheck] = []

    checks.append(_check("app_env", status="pass", required=True, detail=f"app_env={settings.app_env}"))

    if settings.required_provider is not None and settings.required_provider != settings.llm_provider:
        checks.append(
            _check(
                "required_provider",
                status="fail",
                required=True,
                detail=f"required_provider={settings.required_provider} does not match llm_provider={settings.llm_provider}",
            )
        )
    else:
        checks.append(
            _check(
                "required_provider",
                status="pass",
                required=False,
                detail=f"llm_provider={settings.llm_provider}",
            )
        )

    postgres_required = any(
        backend == "postgres"
        for backend in (settings.app_data_backend, settings.auth_store_backend, settings.household_store_backend)
    )
    if postgres_required and not settings.postgres_dsn:
        checks.append(
            _check(
                "postgres_dsn",
                status="fail",
                required=True,
                detail="postgres backend selected but POSTGRES_DSN is missing",
            )
        )
    else:
        checks.append(
            _check(
                "postgres_dsn",
                status="pass",
                required=postgres_required,
                detail="postgres DSN configured" if postgres_required else "postgres backend not selected",
            )
        )

    redis_required = settings.ephemeral_state_backend == "redis"
    if redis_required and not settings.redis_url:
        checks.append(
            _check(
                "redis_url",
                status="fail",
                required=True,
                detail="EPHEMERAL_STATE_BACKEND=redis but REDIS_URL is missing",
            )
        )
    else:
        checks.append(
            _check(
                "redis_url",
                status="pass",
                required=redis_required,
                detail="redis URL configured" if redis_required else "redis backend not selected",
            )
        )

    if redis_required and settings.redis_url:
        ok, detail = _try_redis_ping(str(settings.redis_url))
        checks.append(_check("redis_connectivity", status="pass" if ok else "fail", required=True, detail=detail))
    else:
        checks.append(
            _check(
                "redis_connectivity",
                status="pass",
                required=False,
                detail="skipped (redis backend not selected)",
            )
        )

    shared_rate_limiting_required = settings.app_env in {"staging", "prod"} and settings.api_rate_limit_enabled
    if shared_rate_limiting_required and settings.ephemeral_state_backend != "redis":
        checks.append(
            _check(
                "shared_rate_limiting",
                status="fail",
                required=True,
                detail="shared rate limiting requires EPHEMERAL_STATE_BACKEND=redis when API rate limiting is enabled in staging/prod",
            )
        )
    else:
        checks.append(
            _check(
                "shared_rate_limiting",
                status="pass",
                required=shared_rate_limiting_required,
                detail="shared rate limiting configured" if shared_rate_limiting_required else "shared rate limiting not required",
            )
        )

    if not settings.email_dev_mode and not settings.email_smtp_host:
        checks.append(
            _check(
                "email_configuration",
                status="warn",
                required=False,
                detail="EMAIL_DEV_MODE=false but EMAIL_SMTP_HOST is not configured",
            )
        )
    else:
        checks.append(
            _check(
                "email_configuration",
                status="pass",
                required=False,
                detail="email channel configuration is sufficient for current mode",
            )
        )

    if not settings.sms_dev_mode and not settings.sms_webhook_url:
        checks.append(
            _check(
                "sms_configuration",
                status="warn",
                required=False,
                detail="SMS_DEV_MODE=false but SMS_WEBHOOK_URL is not configured",
            )
        )
    else:
        checks.append(
            _check(
                "sms_configuration",
                status="pass",
                required=False,
                detail="sms channel configuration is sufficient for current mode",
            )
        )

    if not settings.telegram_dev_mode and (not settings.telegram_bot_token or not settings.telegram_chat_id):
        checks.append(
            _check(
                "telegram_configuration",
                status="warn",
                required=False,
                detail="TELEGRAM_DEV_MODE=false but TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID are not fully configured",
            )
        )
    else:
        checks.append(
            _check(
                "telegram_configuration",
                status="pass",
                required=False,
                detail="telegram channel configuration is sufficient for current mode",
            )
        )

    warnings = [item["detail"] for item in checks if item["status"] == "warn"]
    errors = [item["detail"] for item in checks if item["status"] == "fail"]

    has_required_failures = any(item["required"] and item["status"] == "fail" for item in checks)
    if has_required_failures:
        status = "not_ready"
    elif warnings:
        status = "not_ready" if bool(settings.readiness_fail_on_warnings) else "degraded"
    else:
        status = "ready"

    return {
        "status": status,
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
    }
