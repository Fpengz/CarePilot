"""Canonical observability platform exports."""

from care_pilot.platform.observability.context import (
    bind_observability_context,
    current_observability_context,
    get_correlation_id,
    get_request_id,
)
from care_pilot.platform.observability.logging import log_event, observability_span
from care_pilot.platform.observability.setup import get_logger, logger, setup_logging

__all__ = [
    "bind_observability_context",
    "current_observability_context",
    "get_correlation_id",
    "get_logger",
    "get_request_id",
    "log_event",
    "logger",
    "observability_span",
    "setup_logging",
]
