from fastapi import APIRouter, Request

from ..routes_shared import get_context

router = APIRouter(tags=["health"])


@router.get("/api/v1/health/live")
def health_live() -> dict[str, object]:
    return {"status": "ok", "service": "dietary-guardian-api"}


@router.get("/api/v1/health/ready")
def health_ready(request: Request) -> dict[str, object]:
    context = get_context(request)
    return {
        "status": "ready",
        "llm_provider": context.settings.llm_provider,
        "alerts_outbox_v2": context.settings.use_alert_outbox_v2,
    }


@router.get("/api/v1/health/config")
def health_config(request: Request) -> dict[str, object]:
    context = get_context(request)
    return {
        "llm_provider": context.settings.llm_provider,
        "app_timezone": context.settings.app_timezone,
        "api_host": context.settings.api_host,
        "api_port": context.settings.api_port,
        "cookie_secure": context.settings.cookie_secure,
        "workflow_trace_persistence_enabled": context.settings.workflow_trace_persistence_enabled,
    }

