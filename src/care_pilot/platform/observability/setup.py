"""
Configure logging and tracing for the runtime.

This module wires log formatting and optional tracing integrations used by
the application.
"""

from __future__ import annotations

import logging
import os
from typing import Any, cast

from pydantic import ValidationError

import logfire
from care_pilot.config.app import get_settings
from care_pilot.platform.observability.context import get_correlation_id, get_request_id

logfire_api = cast(Any, logfire)
_CONFIGURED = False
_HANDLER_MARKER = "_care_pilot_logfire_handler"
_ROOT_MARKER = "_care_pilot_logging_configured"


class RequestContextFilter(logging.Filter):
    """Inject request context into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Standardize on new context names
        record.request_id = get_request_id() or "-"
        record.correlation_id = get_correlation_id() or "-"
        record.user_id = "-"  # Placeholder for now
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
    global _CONFIGURED
    root = logging.getLogger()
    if _CONFIGURED or getattr(root, _ROOT_MARKER, False):
        _dedupe_logfire_handlers()
        return logging.getLogger(project_name)

    # Note: logfire.configure() is now handled in setup_observability()
    # setup_logging() remains for backward compatibility and stdlib logging config

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


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)


logger = get_logger("care-pilot")


def setup_observability() -> None:
    """Initialize logfire and instrument all supported libraries."""
    settings = get_settings()

    if not settings.observability.logfire_enabled:
        return

    # Configure logfire
    logfire.configure(
        token=settings.observability.logfire_token,
        environment=settings.app.env,
        service_name="care-pilot-api",
    )

    # Instrument infrastructure libraries
    if hasattr(logfire, "instrument_httpx"):
        logfire.instrument_httpx()

    if hasattr(logfire, "instrument_pydantic"):
        logfire.instrument_pydantic()

    # logfire.instrument_sqlalchemy() will be called once we have the engine
    # logfire.instrument_fastapi() will be called in the API entry point
