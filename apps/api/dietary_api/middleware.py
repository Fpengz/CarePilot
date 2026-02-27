from time import perf_counter

from fastapi import Request, Response

from dietary_guardian.logging_config import get_logger
from .observability import get_correlation_id, get_request_id, render_kv_log

logger = get_logger(__name__)


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
    if settings.api_dev_log_verbose:
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
        if settings.api_dev_log_headers:
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
    if settings.api_dev_log_response_headers:
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
