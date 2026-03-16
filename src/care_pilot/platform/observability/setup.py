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

logfire_api = cast(Any, logfire)
_CONFIGURED = False
_HANDLER_MARKER = "_care_pilot_logfire_handler"
_ROOT_MARKER = "_care_pilot_logging_configured"


def _resolve_log_level_name() -> str:
    try:
        return get_settings().observability.log_level.upper()
    except ValidationError:
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

    logfire_api.configure(send_to_logfire=False)

    level_name = _resolve_log_level_name()
    level = getattr(logging, level_name, logging.INFO)
    root.setLevel(level)
    if not _has_logfire_handler():
        use_logfire_handler = os.getenv("CARE_PILOT_USE_LOGFIRE_HANDLER", "0") == "1"
        if use_logfire_handler:
            handler = cast(logging.Handler, logfire.LogfireLoggingHandler())
            setattr(handler, _HANDLER_MARKER, True)
        else:
            handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
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
