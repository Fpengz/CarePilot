"""
Configure logging and tracing for the runtime.

This module wires log formatting and optional tracing integrations used by
the application.
"""

import logging
import os
from typing import Any, cast

from pydantic import ValidationError

import logfire
from care_pilot.config.app import get_settings
from care_pilot.platform.observability.context import (
    get_current_correlation_id,
    get_current_request_id,
    get_current_user_id,
)

logfire_api = cast(Any, logfire)
_CONFIGURED = False
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
    """Old-style logging setup, kept for compatibility."""
    global _CONFIGURED
    root = logging.getLogger()
    if _CONFIGURED or getattr(root, _ROOT_MARKER, False):
        _dedupe_logfire_handlers()
        return logging.getLogger(project_name)

    level_name = _resolve_log_level_name()
    level = getattr(logging, level_name, logging.INFO)
    root.setLevel(level)

    if not _has_logfire_handler():
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

    # Setup standard logging
    setup_logging()

    # Instrument common libraries
    logfire_api.instrument_httpx()


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)


logger = get_logger("care-pilot")
