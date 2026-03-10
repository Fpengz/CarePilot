from __future__ import annotations

import asyncio
from uuid import uuid4

from apps.api.dietary_api.deps import build_app_context, close_app_context
from dietary_guardian.config.settings import get_settings
from dietary_guardian.infrastructure.notifications.alert_outbox import OutboxWorker
from dietary_guardian.observability import get_logger
from dietary_guardian.infrastructure.schedulers.reminder_scheduler import run_reminder_scheduler_once

logger = get_logger(__name__)
_WORKER_FAILURE_RETRY_SECONDS = 1.0


def _idle_wait_seconds(settings) -> float:
    return float(
        min(
            settings.workers.reminder_worker_poll_interval_seconds,
            settings.workers.outbox_worker_poll_interval_seconds,
        )
    )


async def _run_worker_iteration(*, ctx, settings, owner: str) -> bool:
    processed_work = False
    if ctx.coordination_store.acquire_lock(
        "reminder-scheduler",
        owner=owner,
        ttl_seconds=settings.storage.redis_lock_ttl_seconds,
    ):
        try:
            reminder_result = await run_reminder_scheduler_once(repository=ctx.app_store)
            processed_work = processed_work or bool(reminder_result.queued_count or reminder_result.delivery_attempts)
        finally:
            ctx.coordination_store.release_lock("reminder-scheduler", owner=owner)

    if ctx.coordination_store.acquire_lock(
        "outbox-worker",
        owner=owner,
        ttl_seconds=settings.storage.redis_lock_ttl_seconds,
    ):
        try:
            worker = OutboxWorker(
                ctx.app_store,
                lease_owner=owner,
                max_attempts=settings.workers.alert_worker_max_attempts,
                concurrency=settings.workers.alert_worker_concurrency,
            )
            outbox_results = await worker.process_once()
            processed_work = processed_work or bool(outbox_results)
        finally:
            ctx.coordination_store.release_lock("outbox-worker", owner=owner)

    if processed_work:
        return True

    wait_seconds = _idle_wait_seconds(settings)
    wait_for_signal = getattr(ctx.coordination_store, "wait_for_signal", None)
    if callable(wait_for_signal):
        wait_for_signal(
            settings.storage.redis_worker_signal_channel,
            timeout_seconds=wait_seconds,
        )
        return False
    await asyncio.sleep(wait_seconds)
    return False


async def run_worker_loop() -> None:
    settings = get_settings()
    ctx = build_app_context()
    owner = f"worker-{uuid4().hex[:8]}"
    logger.info(
        "worker_loop_start worker_mode=%s ephemeral_state_backend=%s owner=%s",
        settings.workers.worker_mode,
        settings.storage.ephemeral_state_backend,
        owner,
    )
    try:
        while True:
            try:
                processed_work = await _run_worker_iteration(ctx=ctx, settings=settings, owner=owner)
            except Exception:
                logger.exception(
                    "worker_loop_iteration_failed worker_mode=%s ephemeral_state_backend=%s owner=%s retry_in_seconds=%.1f",
                    settings.workers.worker_mode,
                    settings.storage.ephemeral_state_backend,
                    owner,
                    _WORKER_FAILURE_RETRY_SECONDS,
                )
                await asyncio.sleep(_WORKER_FAILURE_RETRY_SECONDS)
                continue
            if processed_work:
                continue
    finally:
        close_app_context(ctx)


def main() -> None:
    asyncio.run(run_worker_loop())


if __name__ == "__main__":
    main()
