from fastapi import APIRouter, Request

from dietary_guardian.services.readiness_service import build_readiness_report

from ..routes_shared import get_context

router = APIRouter(tags=["health"])


@router.get("/api/v1/health/live")
def health_live() -> dict[str, object]:
    return {"status": "ok", "service": "dietary-guardian-api"}


@router.get("/api/v1/health/ready")
def health_ready(request: Request) -> dict[str, object]:
    context = get_context(request)
    report = build_readiness_report(settings=context.settings)
    return {
        "status": report["status"],
        "llm_provider": context.settings.llm_provider,
        "alerts_outbox_v2": context.settings.use_alert_outbox_v2,
        "app_env": context.settings.app_env,
        "checks": report["checks"],
        "warnings": report["warnings"],
        "errors": report["errors"],
    }


@router.get("/api/v1/health/config")
def health_config(request: Request) -> dict[str, object]:
    context = get_context(request)
    return {
        "llm_provider": context.settings.llm_provider,
        "app_env": context.settings.app_env,
        "app_timezone": context.settings.app_timezone,
        "api_host": context.settings.api_host,
        "api_port": context.settings.api_port,
        "cookie_secure": context.settings.cookie_secure,
        "workflow_trace_persistence_enabled": context.settings.workflow_trace_persistence_enabled,
    }
