"""Observability support for logging."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from dietary_guardian.infrastructure.observability.setup import get_logger, logger, setup_logging  # noqa: F401

from .context import bind_observability_context, current_observability_context


def log_event(logger: logging.Logger, level: int, event: str, /, **fields: Any) -> None:  # noqa: F811
    merged_fields = {**current_observability_context(), **fields}
    if merged_fields:
        serialized_fields = " ".join(f"{key}={value}" for key, value in merged_fields.items())
        logger.log(level, "%s %s", event, serialized_fields)
        return
    logger.log(level, "%s", event)


@contextmanager
def observability_span(name: str, /, **context: Any) -> Iterator[None]:
    correlation_id = context.get("correlation_id")
    request_id = context.get("request_id")
    with bind_observability_context(correlation_id=correlation_id, request_id=request_id):
        yield
