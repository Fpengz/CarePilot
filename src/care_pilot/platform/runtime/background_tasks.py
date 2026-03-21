"""
Asynchronous background task queue for side-effects.

This module provides a non-blocking queue to offload tasks like logging,
metrics, and cleanup from the critical request/response path.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

_QUEUE: asyncio.Queue[tuple[Callable[..., Coroutine[Any, Any, Any]], tuple[Any, ...], dict[str, Any]]] = asyncio.Queue(maxsize=1000)

async def enqueue_task(
    func: Callable[..., Coroutine[Any, Any, Any]],
    *args: Any,
    **kwargs: Any
) -> bool:
    """
    Add a task to the background queue.
    Returns True if successfully enqueued, False if queue is full.
    """
    try:
        _QUEUE.put_nowait((func, args, kwargs))
        return True
    except asyncio.QueueFull:
        logger.warning("background_task_queue_full task=%s", getattr(func, "__name__", "unknown"))
        return False

async def run_background_worker() -> None:
    """Infinite loop to process background tasks."""
    logger.info("background_worker_started")
    while True:
        func, args, kwargs = await _QUEUE.get()
        try:
            logger.debug("executing_background_task name=%s", getattr(func, "__name__", "unknown"))
            await func(*args, **kwargs)
        except Exception as exc:
            logger.exception("background_task_failed name=%s error=%s", getattr(func, "__name__", "unknown"), exc)
        finally:
            _QUEUE.task_done()

def get_queue_size() -> int:
    return _QUEUE.qsize()
