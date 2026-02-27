from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response

from dietary_guardian.logging_config import get_logger

logger = get_logger(__name__)


async def request_context_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())

    request.state.request_id = request_id
    request.state.correlation_id = correlation_id

    started = perf_counter()
    response = await call_next(request)
    elapsed_ms = (perf_counter() - started) * 1000.0
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Correlation-ID"] = correlation_id
    logger.info(
        "api_request_complete method=%s path=%s status=%s request_id=%s correlation_id=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        request_id,
        correlation_id,
        elapsed_ms,
    )
    return response
