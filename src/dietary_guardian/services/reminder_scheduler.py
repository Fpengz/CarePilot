from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import cast

from dietary_guardian.config.settings import get_settings
from dietary_guardian.infrastructure.persistence import AppStoreBackend, ReminderSchedulerRepository, build_app_store
from dietary_guardian.logging_config import get_logger
from dietary_guardian.services.alerting_service import OutboxWorker
from dietary_guardian.services.reminder_notification_service import dispatch_due_reminder_notifications

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
    settings = get_settings()
    repo = repository or cast(ReminderSchedulerRepository, build_app_store(settings))
    dispatch_at = now or datetime.now(timezone.utc)
    queued = dispatch_due_reminder_notifications(
        repository=repo,
        now=dispatch_at,
        limit=settings.reminder_scheduler_batch_size,
    )
    if not queued:
        return ReminderSchedulerRunResult(queued_count=0, delivery_attempts=0)
    worker = OutboxWorker(
        repo,
        max_attempts=settings.alert_worker_max_attempts,
        concurrency=min(settings.alert_worker_concurrency, max(1, len(queued))),
    )
    results = await worker.process_once()
    logger.info(
        "reminder_scheduler_run_complete queued_count=%s delivery_attempts=%s",
        len(queued),
        len(results),
    )
    return ReminderSchedulerRunResult(queued_count=len(queued), delivery_attempts=len(results))


async def run_reminder_scheduler_loop() -> None:
    settings = get_settings()
    logger.info(
        "reminder_scheduler_loop_start interval_seconds=%s batch_size=%s",
        settings.reminder_scheduler_interval_seconds,
        settings.reminder_scheduler_batch_size,
    )
    while True:
        await run_reminder_scheduler_once()
        await asyncio.sleep(settings.reminder_scheduler_interval_seconds)
