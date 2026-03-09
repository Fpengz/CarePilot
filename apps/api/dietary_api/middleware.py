from dataclasses import dataclass
from time import perf_counter
from typing import Any, cast

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from dietary_guardian.infrastructure.cache import build_rate_limiter
from dietary_guardian.logging_config import get_logger
from .errors import api_error_payload
from .observability import get_correlation_id, get_request_id, render_kv_log

logger = get_logger(__name__)


@dataclass(frozen=True)
class _RateLimitRule:
    method: str
    path: str
    limit_attr: str
    code: str


_RATE_LIMIT_RULES: tuple[_RateLimitRule, ...] = (
    _RateLimitRule(
        method="POST",
        path="/api/v1/auth/login",
        limit_attr="rate_limit_auth_login_max_requests",
        code="auth.login.rate_limited",
    ),
    _RateLimitRule(
        method="POST",
        path="/api/v1/meal/analyze",
        limit_attr="rate_limit_meal_analyze_max_requests",
        code="meal.analyze.rate_limited",
    ),
    _RateLimitRule(
        method="POST",
        path="/api/v1/recommendations/generate",
        limit_attr="rate_limit_recommendations_generate_max_requests",
        code="recommendations.generate.rate_limited",
    ),
)


def _matching_rate_limit_rule(request: Request) -> _RateLimitRule | None:
    method = request.method.upper()
    path = request.url.path
    for rule in _RATE_LIMIT_RULES:
        if rule.method == method and rule.path == path:
            return rule
    return None


def _rate_limiter_state(request: Request):
    state = request.app.state.__dict__.get("_rate_limiter_state")
    if state is not None:
        return state
    created = build_rate_limiter(request.app.state.ctx.settings)
    request.app.state.__dict__["_rate_limiter_state"] = created
    return created


async def request_context_middleware(request: Request, call_next) -> Response:
    settings = request.app.state.ctx.settings
    request_id = get_request_id(request)
    correlation_id = get_correlation_id(request)

    request.state.request_id = request_id
    request.state.correlation_id = correlation_id

    client_ip = request.client.host if request.client else None
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    user_agent = request.headers.get("user-agent")
    is_preflight = request.method == "OPTIONS" and bool(request.headers.get("access-control-request-method"))
    if settings.api.rate_limit_enabled:
        rule = _matching_rate_limit_rule(request)
        if rule is not None:
            limit = int(cast(Any, getattr(settings.api, rule.limit_attr)))
            allowed, retry_after = _rate_limiter_state(request).allow(
                key=f"{rule.method}:{rule.path}:{client_ip or 'unknown'}",
                limit=limit,
                window_seconds=int(settings.api.rate_limit_window_seconds),
            )
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content=api_error_payload(
                        status_code=429,
                        code=rule.code,
                        message="rate limit exceeded",
                        correlation_id=correlation_id,
                        details={
                            "retry_after_seconds": retry_after,
                            "limit": limit,
                            "window_seconds": int(settings.api.rate_limit_window_seconds),
                        },
                    ),
                )
    if settings.observability.api_dev_log_verbose:
        started_payload: dict[str, object] = {
            "event": "api_request_started",
            "method": request.method,
            "path": request.url.path,
            "request_id": request_id,
            "correlation_id": correlation_id,
            "client_ip": client_ip,
            "origin": origin,
            "referer": referer,
            "user_agent": user_agent,
            "is_preflight": is_preflight,
        }
        if settings.observability.api_dev_log_headers:
            started_payload["request_headers"] = dict(request.headers.items())
        logger.info(render_kv_log(started_payload))

    started = perf_counter()
    response = await call_next(request)
    elapsed_ms = (perf_counter() - started) * 1000.0
    outcome = "success" if response.status_code < 400 else "error"
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Correlation-ID"] = correlation_id
    logger.info(
        render_kv_log(
            {
                "event": "api_request_complete",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "request_id": request_id,
                "correlation_id": correlation_id,
                "outcome": outcome,
                "latency_ms": round(elapsed_ms, 2),
                "duration_ms": round(elapsed_ms, 2),
                "header_contract": "forwarded",
                "client_ip": client_ip,
                "origin": origin,
                "referer": referer,
                "user_agent": user_agent,
                "is_preflight": is_preflight,
            }
        )
    )
    if settings.observability.api_dev_log_response_headers:
        logger.info(
            render_kv_log(
                {
                    "event": "api_response_headers",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "response_headers": dict(response.headers.items()),
                }
            )
        )
    return response
