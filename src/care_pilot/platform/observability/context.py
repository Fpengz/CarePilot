"""
Provide thread-safe and async-safe request context for observability.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)

def set_request_context(*, request_id: str, correlation_id: str, user_id: str | None = None) -> None:
    """Set the current request context."""
    request_id_ctx.set(request_id)
    correlation_id_ctx.set(correlation_id)
    user_id_ctx.set(user_id)

def get_current_request_id() -> str | None:
    return request_id_ctx.get()

def get_current_correlation_id() -> str | None:
    return correlation_id_ctx.get()

def get_current_user_id() -> str | None:
    return user_id_ctx.get()

# Compatibility shims for older code
def get_request_id() -> str | None:
    return get_current_request_id()

def get_correlation_id() -> str | None:
    return get_current_correlation_id()

@contextmanager
def bind_observability_context(request_id: str, correlation_id: str | None = None):
    """Context manager to bind request and correlation IDs."""
    token_req = request_id_ctx.set(request_id)
    token_corr = correlation_id_ctx.set(correlation_id)
    try:
        yield
    finally:
        request_id_ctx.reset(token_req)
        correlation_id_ctx.reset(token_corr)

def current_observability_context() -> dict[str, Any]:
    """Return the current observability context as a dictionary."""
    return {
        "request_id": get_request_id(),
        "correlation_id": get_correlation_id(),
        "user_id": get_current_user_id(),
    }
