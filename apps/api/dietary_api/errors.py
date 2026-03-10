"""Module for errors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from apps.api.dietary_api.observability import render_kv_log
from dietary_guardian.infrastructure.observability import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class ApiAppError(Exception):
    status_code: int
    code: str
    message: str
    details: dict[str, object] = field(default_factory=dict)
    headers: dict[str, str] | None = None


def api_error_payload(
    *,
    status_code: int,
    code: str,
    message: str,
    correlation_id: str | None,
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "detail": message,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "correlation_id": correlation_id,
            "status_code": status_code,
        },
    }


def _failure_metadata(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "event": "api_request_failed",
        "method": request.method,
        "path": request.url.path,
        "status_code": status_code,
        "error_code": code,
        "error_message": message,
        "request_id": getattr(request.state, "request_id", None),
        "correlation_id": getattr(request.state, "correlation_id", None),
        "failure_metadata": details or {},
    }


async def handle_api_app_error(request: Request, exc: ApiAppError) -> JSONResponse:
    metadata = _failure_metadata(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )
    logger.warning(render_kv_log(metadata))
    body = api_error_payload(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        correlation_id=getattr(request.state, "correlation_id", None),
        details=exc.details,
    )
    return JSONResponse(content=body, status_code=exc.status_code, headers=exc.headers)


def _http_error_code(status_code: int) -> str:
    mapping = {
        400: "request.bad_request",
        401: "auth.unauthorized",
        403: "auth.forbidden",
        404: "request.not_found",
        409: "request.conflict",
        422: "request.validation_error",
    }
    return mapping.get(status_code, "request.error")


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    message = str(exc.detail)
    code = _http_error_code(exc.status_code)
    metadata = _failure_metadata(
        request=request,
        status_code=exc.status_code,
        code=code,
        message=message,
        details={},
    )
    logger.warning(render_kv_log(metadata))
    body = api_error_payload(
        status_code=exc.status_code,
        code=code,
        message=message,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return JSONResponse(content=body, status_code=exc.status_code, headers=exc.headers)


async def handle_validation_exception(request: Request, exc: RequestValidationError) -> JSONResponse:
    code = _http_error_code(422)
    message = "request validation failed"
    details = {"errors": exc.errors()}
    metadata = _failure_metadata(
        request=request,
        status_code=422,
        code=code,
        message=message,
        details=details,
    )
    logger.warning(render_kv_log(metadata))
    body = api_error_payload(
        status_code=422,
        code=code,
        message=message,
        correlation_id=getattr(request.state, "correlation_id", None),
        details=details,
    )
    return JSONResponse(content=body, status_code=422)


async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("event=api_request_failed_unhandled path=%s method=%s", request.url.path, request.method)
    body = api_error_payload(
        status_code=500,
        code="internal.server_error",
        message="internal server error",
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return JSONResponse(content=body, status_code=500)


def build_api_error(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> ApiAppError:
    return ApiAppError(
        status_code=status_code,
        code=code,
        message=message,
        details={str(k): v for k, v in (details or {}).items()},
    )
