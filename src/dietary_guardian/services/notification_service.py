from datetime import datetime, timezone

from uuid import uuid4

from pydantic import BaseModel

from dietary_guardian.config.settings import get_settings
from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.alerting import AlertDeliveryResult, AlertMessage, AlertSeverity
from dietary_guardian.models.medication import ReminderEvent
from dietary_guardian.services.alerting_service import AlertPublisher, OutboxWorker
from dietary_guardian.services.channels import TelegramChannel, WeChatChannel, WhatsAppChannel
from dietary_guardian.services.channels.base import ChannelResult
from dietary_guardian.services.repository import SQLiteRepository

logger = get_logger(__name__)
PENDING_ALERT_STATES = {"pending", "processing"}

class DeliveryResult(BaseModel):
    event_id: str
    channel: str
    success: bool
    attempts: int = 1
    error: str | None = None
    delivered_at: datetime | None = None
    destination: str | None = None


def send_in_app(reminder_event: ReminderEvent) -> DeliveryResult:
    destination = "app://inbox"
    logger.info(
        "send_in_app event_id=%s channel=in_app destination=%s attempt=1 success=true user_id=%s medication=%s",
        reminder_event.id,
        destination,
        reminder_event.user_id,
        reminder_event.medication_name,
    )
    return DeliveryResult(
        event_id=reminder_event.id,
        channel="in_app",
        success=True,
        delivered_at=datetime.now(timezone.utc),
        destination=destination,
    )


def send_push(reminder_event: ReminderEvent, force_fail: bool = False) -> DeliveryResult:
    destination = "push://default"
    logger.info(
        "send_push_attempt event_id=%s channel=push destination=%s attempt=1 user_id=%s medication=%s force_fail=%s",
        reminder_event.id,
        destination,
        reminder_event.user_id,
        reminder_event.medication_name,
        force_fail,
    )
    if force_fail:
        logger.warning(
            "send_push_failed event_id=%s channel=push destination=%s attempt=1 success=false reason=forced_failure",
            reminder_event.id,
            destination,
        )
        return DeliveryResult(
            event_id=reminder_event.id,
            channel="push",
            success=False,
            attempts=1,
            error="push delivery failed",
            destination=destination,
        )
    return DeliveryResult(
        event_id=reminder_event.id,
        channel="push",
        success=True,
        delivered_at=datetime.now(timezone.utc),
        destination=destination,
    )


def _channel_from_name(channel: str):
    if channel == "telegram":
        return TelegramChannel()
    if channel == "whatsapp":
        return WhatsAppChannel()
    if channel == "wechat":
        return WeChatChannel()
    return None


def _delivery_from_channel_result(
    event_id: str,
    channel_result: ChannelResult,
) -> DeliveryResult:
    return DeliveryResult(
        event_id=event_id,
        channel=channel_result.channel,
        success=channel_result.success,
        attempts=channel_result.attempts,
        error=channel_result.error,
        delivered_at=channel_result.delivered_at,
        destination=channel_result.destination,
    )


def dispatch_reminder(
    reminder_event: ReminderEvent,
    channels: list[str],
    retries: int = 2,
    force_push_fail: bool = False,
    repository: SQLiteRepository | None = None,
) -> list[DeliveryResult]:
    settings = get_settings()
    if settings.use_alert_outbox_v2 and repository is not None:
        return dispatch_reminder_async(
            reminder_event,
            channels,
            repository=repository,
            retries=retries,
            force_push_fail=force_push_fail,
        )

    logger.info(
        "dispatch_reminder_start event_id=%s channels=%s retries=%s",
        reminder_event.id,
        channels,
        retries,
    )
    results: list[DeliveryResult] = []
    for channel in channels:
        if channel == "in_app":
            results.append(send_in_app(reminder_event))
            continue
        if channel == "push":
            attempt = 0
            latest = DeliveryResult(
                event_id=reminder_event.id,
                channel="push",
                success=False,
                attempts=0,
                error="push delivery failed",
                destination="push://default",
            )
            while attempt <= retries:
                attempt += 1
                latest = send_push(reminder_event, force_fail=force_push_fail)
                latest.attempts = attempt
                if latest.success:
                    logger.info(
                        "dispatch_reminder_push_delivered event_id=%s channel=push destination=%s attempt=%s success=true",
                        reminder_event.id,
                        latest.destination,
                        attempt,
                    )
                    break
            if not latest.success:
                logger.warning(
                    "dispatch_reminder_push_exhausted event_id=%s channel=push destination=%s attempt=%s success=false",
                    reminder_event.id,
                    latest.destination,
                    latest.attempts,
                )
            results.append(latest)
            continue

        extra_channel = _channel_from_name(channel)
        if extra_channel is not None:
            channel_result = extra_channel.send(reminder_event)
            logger.info(
                "dispatch_reminder_channel_result event_id=%s channel=%s success=%s destination=%s",
                reminder_event.id,
                channel_result.channel,
                channel_result.success,
                channel_result.destination,
            )
            results.append(_delivery_from_channel_result(reminder_event.id, channel_result))
            continue

        if channel != "push":
            logger.error(
                "dispatch_reminder_unknown_channel event_id=%s channel=%s",
                reminder_event.id,
                channel,
            )
            results.append(
                DeliveryResult(
                    event_id=reminder_event.id,
                    channel=channel,
                    success=False,
                    error="unknown channel",
                )
            )
            continue
    logger.info("dispatch_reminder_complete event_id=%s results=%s", reminder_event.id, len(results))
    return results


def dispatch_reminder_async(
    reminder_event: ReminderEvent,
    channels: list[str],
    repository: SQLiteRepository | None = None,
    retries: int | None = None,
    force_push_fail: bool = False,
) -> list[DeliveryResult]:
    repo = repository or SQLiteRepository()
    settings = get_settings()
    publisher = AlertPublisher(repo)
    worker = OutboxWorker(
        repo,
        max_attempts=(retries + 1) if retries is not None else settings.alert_worker_max_attempts,
        concurrency=settings.alert_worker_concurrency,
    )
    if force_push_fail and "push" in channels:
        class _ForcedFailPushSink:
            name = "push"

            def send(self, message: AlertMessage) -> AlertDeliveryResult:
                return AlertDeliveryResult(
                    alert_id=message.alert_id,
                    sink="push",
                    success=False,
                    attempt=1,
                    destination="push://default",
                    error="push delivery failed",
                    provider_reference="push",
                )

        worker._sinks["push"] = _ForcedFailPushSink()
    message = AlertMessage(
        alert_id=reminder_event.id,
        type="medication_reminder",
        severity="warning",
        payload={
            "message": f"{reminder_event.medication_name} {reminder_event.dosage_text}",
            "user_id": reminder_event.user_id,
            "medication_name": reminder_event.medication_name,
            "dosage_text": reminder_event.dosage_text,
            "scheduled_at": reminder_event.scheduled_at.isoformat(),
        },
        destinations=channels,
        correlation_id=str(uuid4()),
    )
    publisher.publish(message)
    channel_results = _drain_alert_for_sync_delivery(
        worker,
        repo,
        message.alert_id,
        fast_forward_scheduled_retries=True,
    )
    results = [
        DeliveryResult(
            event_id=result.alert_id,
            channel=result.sink,
            success=result.success,
            attempts=result.attempt,
            error=result.error,
            destination=result.destination,
            delivered_at=datetime.now(timezone.utc) if result.success else None,
        )
        for result in channel_results
        if result.alert_id == message.alert_id
    ]
    logger.info("dispatch_reminder_async_complete event_id=%s results=%s", reminder_event.id, len(results))
    return results


def trigger_alert(
    *,
    alert_type: str,
    severity: AlertSeverity,
    payload: dict[str, str],
    destinations: list[str],
    repository: SQLiteRepository,
) -> tuple[AlertMessage, list[DeliveryResult]]:
    alert = AlertMessage(
        alert_id=str(uuid4()),
        type=alert_type,
        severity=severity,
        payload=payload,
        destinations=destinations,
        correlation_id=str(uuid4()),
    )
    publisher = AlertPublisher(repository)
    publisher.publish(alert)
    worker = OutboxWorker(
        repository,
        max_attempts=get_settings().alert_worker_max_attempts,
        concurrency=get_settings().alert_worker_concurrency,
    )
    channel_results = _drain_alert_for_sync_delivery(
        worker,
        repository,
        alert.alert_id,
        fast_forward_scheduled_retries=False,
    )
    channel_results = [item for item in channel_results if item.alert_id == alert.alert_id]
    results = [
        DeliveryResult(
            event_id=item.alert_id,
            channel=item.sink,
            success=item.success,
            attempts=item.attempt,
            error=item.error,
            destination=item.destination,
            delivered_at=datetime.now(timezone.utc) if item.success else None,
        )
        for item in channel_results
    ]
    return alert, results


def _drain_alert_for_sync_delivery(
    worker: OutboxWorker,
    repository: SQLiteRepository,
    alert_id: str,
    *,
    fast_forward_scheduled_retries: bool,
) -> list[AlertDeliveryResult]:
    asyncio = __import__("asyncio")
    by_sink: dict[str, AlertDeliveryResult] = {}

    while True:
        batch = asyncio.run(worker.process_once(alert_id=alert_id))
        for item in batch:
            by_sink[item.sink] = item

        records = repository.list_alert_records(alert_id)
        pending = [record for record in records if record.state in PENDING_ALERT_STATES]
        if not pending:
            break

        now = datetime.now(timezone.utc)
        if any(record.next_attempt_at <= now for record in pending):
            continue

        if not fast_forward_scheduled_retries:
            break

        for record in pending:
            repository.reschedule_alert(
                alert_id=record.alert_id,
                sink=record.sink,
                next_attempt_at=now,
                attempt_count=record.attempt_count,
                error=record.last_error or "",
            )

    return list(by_sink.values())
