"""Reminder notification scheduler runtime loop.

``run_reminder_scheduler_once`` performs one scheduling tick: it dispatches
due notifications and drains the outbox worker.

``run_reminder_scheduler_loop`` runs the above in a continuous async loop
using the configured interval from settings.

This module is a runtime concern — it should only be imported by process
entrypoints (``apps/api/run_reminder_scheduler.py``, ``apps/workers/run.py``).
Business logic lives in ``application.notifications``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from dietary_guardian.application.contracts.notifications import ReminderSchedulerRepository
from dietary_guardian.application.notifications.reminder_materialization import (
    dispatch_due_reminder_notifications,
)
from dietary_guardian.config.settings import get_settings
from dietary_guardian.infrastructure.notifications.alert_outbox import OutboxWorker
from dietary_guardian.infrastructure.persistence import AppStoreBackend
from dietary_guardian.observability import get_logger
from dietary_guardian.runtime.bootstrap.dependencies import build_reminder_scheduler_repository

logger = get_logger(__name__)


@dataclass(slots=True)
class ReminderSchedulerRunResult:
    queued_count: int
    delivery_attempts: int


async def run_reminder_scheduler_once(
    *,
    repository: ReminderSchedulerRepository | AppStoreBackend | None = None,
    now: datetime | None = None,
) -> ReminderSchedulerRunResult:
    """Dispatch due reminders and process the outbox once."""
    settings = get_settings()
    repo = repository or build_reminder_scheduler_repository(settings)
    dispatch_at = now or datetime.now(timezone.utc)
    queued = dispatch_due_reminder_notifications(
        repository=repo,
        now=dispatch_at,
        limit=settings.workers.reminder_scheduler_batch_size,
    )
    if not queued:
        return ReminderSchedulerRunResult(queued_count=0, delivery_attempts=0)
    worker = OutboxWorker(
        repo,
        max_attempts=settings.workers.alert_worker_max_attempts,
        concurrency=min(settings.workers.alert_worker_concurrency, max(1, len(queued))),
    )
    results = await worker.process_once()
    logger.info(
        "reminder_scheduler_run_complete queued_count=%s delivery_attempts=%s",
        len(queued),
        len(results),
    )
    return ReminderSchedulerRunResult(queued_count=len(queued), delivery_attempts=len(results))


async def run_reminder_scheduler_loop() -> None:
    """Run the reminder scheduler in an infinite loop."""
    settings = get_settings()
    logger.info(
        "reminder_scheduler_loop_start interval_seconds=%s batch_size=%s",
        settings.workers.reminder_scheduler_interval_seconds,
        settings.workers.reminder_scheduler_batch_size,
    )
    while True:
        await run_reminder_scheduler_once()
        await asyncio.sleep(settings.workers.reminder_scheduler_interval_seconds)


__all__ = [
    "ReminderSchedulerRunResult",
    "run_reminder_scheduler_loop",
    "run_reminder_scheduler_once",
]
