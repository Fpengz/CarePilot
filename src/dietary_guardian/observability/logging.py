from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from dietary_guardian.logging_config import (
    get_logger as _get_logger,
    logger as _root_logger,
    setup_logging as _setup_logging,
)

from .context import bind_observability_context, current_observability_context

get_logger = _get_logger
logger = _root_logger
setup_logging = _setup_logging


def log_event(logger: logging.Logger, level: int, event: str, /, **fields: Any) -> None:
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
