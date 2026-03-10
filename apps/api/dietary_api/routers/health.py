from fastapi import APIRouter, Depends, HTTPException, Request

from dietary_guardian.infrastructure.diagnostics.readiness import build_readiness_report

from ..routes_shared import current_session, get_context

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
        "llm_provider": context.settings.llm.provider,
        "alerts_outbox_v2": context.settings.workers.use_alert_outbox_v2,
        "app_env": context.settings.app.env,
        "checks": report["checks"],
        "warnings": report["warnings"],
        "errors": report["errors"],
    }


@router.get("/api/v1/health/config")
def health_config(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> dict[str, object]:
    if str(session.get("account_role", "")) != "admin":
        raise HTTPException(status_code=403, detail="forbidden")
    context = get_context(request)
    return {
        "llm_provider": context.settings.llm.provider,
        "app_env": context.settings.app.env,
        "app_timezone": context.settings.app.timezone,
        "api_host": context.settings.api.host,
        "api_port": context.settings.api.port,
        "cookie_secure": context.settings.auth.cookie_secure,
        "workflow_trace_persistence_enabled": context.settings.workers.workflow_trace_persistence_enabled,
    }
