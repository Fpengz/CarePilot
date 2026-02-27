from uuid import uuid4

from fastapi import Request, Response


async def request_context_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())

    request.state.request_id = request_id
    request.state.correlation_id = correlation_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Correlation-ID"] = correlation_id
    return response
