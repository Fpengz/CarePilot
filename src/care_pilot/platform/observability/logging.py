"""
Configure logging and tracing for the runtime.

This module wires log formatting and optional tracing integrations used by
the application, and provides structured logging helpers.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, cast

from pydantic import ValidationError

import logfire
from care_pilot.config.app import get_settings
from care_pilot.platform.observability.context import (
    bind_observability_context,
    current_observability_context,
    get_current_correlation_id,
    get_current_request_id,
    get_current_user_id,
)

logfire_api = cast(Any, logfire)
_CONFIGURED = False
_LOGFIRE_CONFIGURED = False
_HANDLER_MARKER = "_care_pilot_logfire_handler"
_ROOT_MARKER = "_care_pilot_logging_configured"


class RequestContextFilter(logging.Filter):
    """Inject request context into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_current_request_id() or "-"
        record.correlation_id = get_current_correlation_id() or "-"
        record.user_id = get_current_user_id() or "-"
        return True


def _resolve_log_level_name() -> str:
    try:
        return get_settings().observability.log_level.upper()
    except (ValidationError, RuntimeError):
        return os.getenv("CARE_PILOT_LOG_LEVEL", "INFO").upper()


def _has_logfire_handler() -> bool:
    root = logging.getLogger()
    return any(
        getattr(handler, _HANDLER_MARKER, False)
        or handler.__class__.__name__ == "LogfireLoggingHandler"
        for handler in root.handlers
    )


def _dedupe_logfire_handlers() -> None:
    root = logging.getLogger()
    keep_one = False
    handlers: list[logging.Handler] = []
    for handler in root.handlers:
        is_logfire = (
            getattr(handler, _HANDLER_MARKER, False)
            or handler.__class__.__name__ == "LogfireLoggingHandler"
        )
        if is_logfire:
            if keep_one:
                continue
            setattr(handler, _HANDLER_MARKER, True)
            keep_one = True
        handlers.append(handler)
    root.handlers = handlers


def setup_logging(project_name: str = "care-pilot") -> logging.Logger:
    """Configure standard Python logging."""
    global _CONFIGURED, _LOGFIRE_CONFIGURED
    root = logging.getLogger()
    if _CONFIGURED or getattr(root, _ROOT_MARKER, False):
        _dedupe_logfire_handlers()
        return logging.getLogger(project_name)

    # Ensure logfire is at least minimally configured if it hasn't been yet
    if not _LOGFIRE_CONFIGURED:
        logfire_api.configure(send_to_logfire=False)
        _LOGFIRE_CONFIGURED = True

    level_name = _resolve_log_level_name()
    level = getattr(logging, level_name, logging.INFO)
    root.setLevel(level)

    if not _has_logfire_handler():
        use_logfire_handler = os.getenv("CARE_PILOT_USE_LOGFIRE_HANDLER", "0") == "1"
        if use_logfire_handler:
            handler = cast(logging.Handler, logfire.LogfireLoggingHandler())
        else:
            handler = logging.StreamHandler()
        setattr(handler, _HANDLER_MARKER, True)
        handler.setLevel(level)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] [req=%(request_id)s corr=%(correlation_id)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        handler.addFilter(RequestContextFilter())
        root.addHandler(handler)

    _dedupe_logfire_handlers()
    logger = logging.getLogger(project_name)
    logger.setLevel(level)
    setattr(root, _ROOT_MARKER, True)
    _CONFIGURED = True
    return logger


def setup_observability() -> None:
    """Unified entry point for observability (logging + logfire)."""
    global _LOGFIRE_CONFIGURED
    settings = get_settings()

    # Configure logfire
    token = settings.observability.logfire_token
    env = settings.app.env

    if token:
        logfire_api.configure(
            token=token,
            environment=env,
            service_name="care-pilot",
            send_to_logfire=True
        )
    else:
        logfire_api.configure(send_to_logfire=False)
    _LOGFIRE_CONFIGURED = True

    # Setup standard logging
    setup_logging()

    # Instrument common libraries
    logfire_api.instrument_httpx()


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)


logger = get_logger("care-pilot")


def log_event(logger: logging.Logger, level: int, event: str, /, **fields: Any) -> None:
    merged_fields = {**current_observability_context(), **fields}
    if merged_fields:
        serialized_fields = " ".join(f"{key}={value}" for key, value in merged_fields.items())
        logger.log(level, "%s %s", event, serialized_fields)
        return
    logger.log(level, "%s", event)


@contextmanager
def observability_span(_name: str, /, **context: Any) -> Iterator[None]:
    correlation_id = context.get("correlation_id")
    request_id = context.get("request_id")
    with bind_observability_context(correlation_id=correlation_id, request_id=request_id):
        yield
