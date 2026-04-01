"""Canonical observability platform exports."""

from care_pilot.platform.observability.context import (
    bind_observability_context,
    current_observability_context,
    get_correlation_id,
    get_request_id,
)
from care_pilot.platform.observability.logging import (
    get_logger,
    log_event,
    logger,
    observability_span,
    setup_logging,
)
from care_pilot.platform.observability.setup import setup_observability

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
    "setup_observability",
]
