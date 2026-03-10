"""System readiness diagnostic report.

``build_readiness_report`` inspects settings and live connectivity to produce
a structured report used by the ``/health/ready`` endpoint.  All checks are
synchronous and safe to call at startup.
"""

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
    return {"name": name, "status": status, "required": required, "detail": detail}


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
    """Return a readiness report by inspecting settings and probing live services."""
    checks: list[ReadinessCheck] = []

    checks.append(_check("app_env", status="pass", required=True, detail=f"app_env={settings.app.env}"))

    if settings.llm.required_provider is not None and settings.llm.required_provider != settings.llm.provider:
        checks.append(
            _check(
                "required_provider",
                status="fail",
                required=True,
                detail=f"required_provider={settings.llm.required_provider} does not match llm_provider={settings.llm.provider}",
            )
        )
    else:
        checks.append(
            _check(
                "required_provider",
                status="pass",
                required=False,
                detail=f"llm_provider={settings.llm.provider}",
            )
        )

    checks.append(
        _check(
            "durable_storage",
            status="pass",
            required=True,
            detail=(
                "sqlite durable stores configured "
                f"(app={settings.storage.app_data_backend}, auth={settings.auth.store_backend}, household={settings.storage.household_store_backend})"
            ),
        )
    )

    redis_required = settings.storage.ephemeral_state_backend == "redis"
    if redis_required and not settings.storage.redis_url:
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

    if redis_required and settings.storage.redis_url:
        ok, detail = _try_redis_ping(str(settings.storage.redis_url))
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

    shared_rate_limiting_required = settings.app.env in {"staging", "prod"} and settings.api.rate_limit_enabled
    if shared_rate_limiting_required and settings.storage.ephemeral_state_backend != "redis":
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

    if not settings.channels.email_dev_mode and not settings.channels.email_smtp_host:
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

    if not settings.channels.sms_dev_mode and not settings.channels.sms_webhook_url:
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

    if not settings.channels.telegram_dev_mode and (not settings.channels.telegram_bot_token or not settings.channels.telegram_chat_id):
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
        status = "not_ready" if bool(settings.observability.readiness_fail_on_warnings) else "degraded"
    else:
        status = "ready"

    return {
        "status": status,
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
    }


__all__ = ["ReadinessCheck", "ReadinessReport", "build_readiness_report"]
