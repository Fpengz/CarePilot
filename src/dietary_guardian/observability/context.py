from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

_correlation_id_var: ContextVar[str | None] = ContextVar("dietary_guardian_correlation_id", default=None)
_request_id_var: ContextVar[str | None] = ContextVar("dietary_guardian_request_id", default=None)


def get_correlation_id() -> str | None:
    return _correlation_id_var.get()


def get_request_id() -> str | None:
    return _request_id_var.get()


def current_observability_context() -> dict[str, str]:
    context: dict[str, str] = {}
    correlation_id = get_correlation_id()
    request_id = get_request_id()
    if correlation_id is not None:
        context["correlation_id"] = correlation_id
    if request_id is not None:
        context["request_id"] = request_id
    return context


@contextmanager
def bind_observability_context(*, correlation_id: str | None = None, request_id: str | None = None) -> Iterator[None]:
    correlation_token = None
    request_token = None
    if correlation_id is not None:
        correlation_token = _correlation_id_var.set(correlation_id)
    if request_id is not None:
        request_token = _request_id_var.set(request_id)
    try:
        yield
    finally:
        if correlation_token is not None:
            _correlation_id_var.reset(correlation_token)
        if request_token is not None:
            _request_id_var.reset(request_token)
