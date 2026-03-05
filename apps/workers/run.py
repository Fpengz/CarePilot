from __future__ import annotations

import asyncio
from uuid import uuid4

from apps.api.dietary_api.deps import build_app_context, close_app_context
from dietary_guardian.config.settings import get_settings
from dietary_guardian.logging_config import get_logger
from dietary_guardian.services.alerting_service import OutboxWorker
from dietary_guardian.services.reminder_scheduler import run_reminder_scheduler_once

logger = get_logger(__name__)


async def run_worker_loop() -> None:
    settings = get_settings()
    ctx = build_app_context()
    owner = f"worker-{uuid4().hex[:8]}"
    logger.info(
        "worker_loop_start worker_mode=%s ephemeral_state_backend=%s owner=%s",
        settings.worker_mode,
        settings.ephemeral_state_backend,
        owner,
    )
    try:
        while True:
            processed_work = False
            if ctx.coordination_store.acquire_lock(
                "reminder-scheduler",
                owner=owner,
                ttl_seconds=settings.redis_lock_ttl_seconds,
            ):
                try:
                    reminder_result = await run_reminder_scheduler_once(repository=ctx.repository)
                    processed_work = processed_work or bool(reminder_result.queued_count or reminder_result.delivery_attempts)
                finally:
                    ctx.coordination_store.release_lock("reminder-scheduler", owner=owner)

            if ctx.coordination_store.acquire_lock(
                "outbox-worker",
                owner=owner,
                ttl_seconds=settings.redis_lock_ttl_seconds,
            ):
                try:
                    worker = OutboxWorker(
                        ctx.repository,
                        lease_owner=owner,
                        max_attempts=settings.alert_worker_max_attempts,
                        concurrency=settings.alert_worker_concurrency,
                    )
                    outbox_results = await worker.process_once()
                    processed_work = processed_work or bool(outbox_results)
                finally:
                    ctx.coordination_store.release_lock("outbox-worker", owner=owner)

            if processed_work:
                continue

            wait_seconds = float(
                min(
                    settings.reminder_worker_poll_interval_seconds,
                    settings.outbox_worker_poll_interval_seconds,
                )
            )
            wait_for_signal = getattr(ctx.coordination_store, "wait_for_signal", None)
            if callable(wait_for_signal):
                wait_for_signal(
                    settings.redis_worker_signal_channel,
                    timeout_seconds=wait_seconds,
                )
                continue
            await asyncio.sleep(wait_seconds)
    finally:
        close_app_context(ctx)


def main() -> None:
    asyncio.run(run_worker_loop())


if __name__ == "__main__":
    main()
