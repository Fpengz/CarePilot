"""Module for observability."""

from __future__ import annotations

import re
from uuid import uuid4

from fastapi import Request

_TRACE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$")


def _normalize_trace_id(value: object | None) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if not _TRACE_ID_PATTERN.fullmatch(candidate):
        return None
    return candidate


def get_request_id(request: Request) -> str:
    value = _normalize_trace_id(request.headers.get("X-Request-ID")) or _normalize_trace_id(
        getattr(request.state, "request_id", None)
    )
    return value or str(uuid4())


def get_correlation_id(request: Request) -> str:
    value = _normalize_trace_id(request.headers.get("X-Correlation-ID")) or _normalize_trace_id(
        getattr(request.state, "correlation_id", None)
    )
    return value or str(uuid4())


def render_kv_log(payload: dict[str, object]) -> str:
    return " ".join(f"{key}={value}" for key, value in payload.items() if value is not None)
