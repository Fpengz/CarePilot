"""Alert outbox delivery worker and publisher.

``OutboxWorker`` leases ``OutboxRecord`` rows from the repository, routes each
record to the appropriate ``SinkAdapter``, and handles retry/dead-letter
semantics.  ``AlertPublisher`` is a thin helper that enqueues an
``AlertMessage`` into the outbox.

Concrete sink adapters live in
``care_pilot.platform.messaging.channels.sinks`` and are imported here
for backward compatibility.
"""

from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime, timedelta
from typing import cast

from care_pilot.core.contracts.notifications import AlertRepositoryProtocol
from care_pilot.features.reminders.domain.models import MessageChannel
from care_pilot.features.safety.domain.alerts import (
    AlertDeliveryResult,
    OutboundMessage,
    OutboxRecord,
)
from care_pilot.platform.messaging.channels.base import SinkAdapter  # noqa: F401
from care_pilot.platform.messaging.channels.sinks import (  # noqa: F401
    EmailSink,
    InAppSink,
    PushSink,
    SmsSink,
    TelegramSink,
    WeChatSink,
    WhatsAppSink,
)
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


class AlertPublisher:
    """Enqueues an ``AlertMessage`` into the outbox repository."""

    def __init__(self, repository: AlertRepositoryProtocol) -> None:
        self._repository = repository

    def publish(self, message: OutboundMessage) -> list[OutboxRecord]:
        logger.info(
            "alert_publish alert_id=%s correlation_id=%s destinations=%s",
            message.alert_id,
            message.correlation_id,
            message.destinations,
        )
        return self._repository.enqueue_alert(message)


class OutboxWorker:
    """Processes leased outbox records and routes to the appropriate sink."""

    def __init__(
        self,
        repository: AlertRepositoryProtocol,
        lease_owner: str = "worker-1",
        max_attempts: int = 3,
        concurrency: int = 4,
    ) -> None:
        self._repository = repository
        self._lease_owner = lease_owner
        self._max_attempts = max_attempts
        self._concurrency = concurrency
        self._sinks: dict[str, SinkAdapter] = {
            "in_app": InAppSink(),
            "push": PushSink(),
            "email": EmailSink(),
            "sms": SmsSink(),
            "telegram": TelegramSink(),
            "whatsapp": WhatsAppSink(),
            "wechat": WeChatSink(),
        }

    async def process_once(self, alert_id: str | None = None) -> list[AlertDeliveryResult]:
        now = datetime.now(UTC)
        leased = self._repository.lease_alert_records(
            now=now,
            lease_owner=self._lease_owner,
            lease_seconds=30,
            limit=self._concurrency,
            alert_id=alert_id,
        )
        if not leased:
            return []
        logger.info(
            "alert_outbox_leased count=%s alert_id_filter=%s",
            len(leased),
            alert_id or "none",
        )

        tasks = [self._deliver_record(record) for record in leased]
        return await asyncio.gather(*tasks)

    async def _deliver_record(self, record: OutboxRecord) -> AlertDeliveryResult:
        sink = self._sinks.get(record.sink)
        if sink is None:
            self._sync_reminder_notification_dead_letter(
                record=record,
                attempt=record.attempt_count + 1,
                error="unknown sink",
            )
            self._repository.mark_alert_dead_letter(
                record.alert_id,
                record.sink,
                "unknown sink",
                attempt_count=record.attempt_count + 1,
            )
            return AlertDeliveryResult(
                alert_id=record.alert_id,
                sink=record.sink,
                success=False,
                attempt=record.attempt_count + 1,
                error="unknown sink",
            )

        message = OutboundMessage(
            alert_id=record.alert_id,
            type=record.type,
            severity=record.severity,
            payload=record.payload,
            destinations=[record.sink],
            correlation_id=record.correlation_id,
            attachments=record.attachments,
            created_at=record.created_at,
        )
        attempt = record.attempt_count + 1
        self._sync_reminder_notification_processing(record=record, attempt=attempt)
        logger.info(
            "alert_delivery_attempt alert_id=%s sink=%s attempt=%s",
            record.alert_id,
            record.sink,
            attempt,
        )
        try:
            result = sink.send(message)
        except Exception as exc:
            logger.exception(
                "alert_delivery_sink_error alert_id=%s sink=%s attempt=%s error=%s",
                record.alert_id,
                record.sink,
                attempt,
                exc,
            )
            result = AlertDeliveryResult(
                alert_id=record.alert_id,
                sink=record.sink,
                success=False,
                attempt=attempt,
                error=str(exc),
            )

        if result.success:
            self._repository.mark_alert_delivered(
                record.alert_id, record.sink, attempt_count=attempt
            )
            self._sync_reminder_notification_delivered(record=record, attempt=attempt)
            logger.info(
                "alert_delivery_success alert_id=%s sink=%s attempt=%s",
                record.alert_id,
                record.sink,
                attempt,
            )
            return result.model_copy(update={"attempt": attempt})

        if attempt >= self._max_attempts:
            self._sync_reminder_notification_dead_letter(
                record=record,
                attempt=attempt,
                error=result.error or "delivery failed",
            )
            self._repository.mark_alert_dead_letter(
                record.alert_id,
                record.sink,
                result.error or "delivery failed",
                attempt_count=attempt,
            )
            logger.warning(
                "alert_delivery_dead_letter alert_id=%s sink=%s attempt=%s error=%s",
                record.alert_id,
                record.sink,
                attempt,
                result.error or "delivery failed",
            )
            return result.model_copy(update={"attempt": attempt})

        delay_seconds = (2**attempt) + random.randint(0, 2)
        next_attempt = datetime.now(UTC) + timedelta(seconds=delay_seconds)
        self._sync_reminder_notification_retry(
            record=record,
            attempt=attempt,
            next_attempt_at=next_attempt,
            error=result.error or "delivery failed",
        )
        self._repository.reschedule_alert(
            alert_id=record.alert_id,
            sink=record.sink,
            next_attempt_at=next_attempt,
            attempt_count=attempt,
            error=result.error or "delivery failed",
        )
        logger.warning(
            "alert_delivery_retry alert_id=%s sink=%s attempt=%s next_attempt_at=%s error=%s",
            record.alert_id,
            record.sink,
            attempt,
            next_attempt.isoformat(),
            result.error or "delivery failed",
        )
        return result.model_copy(update={"attempt": attempt})

    # --- reminder notification lifecycle sync helpers ---

    def _sync_reminder_notification_processing(self, *, record: OutboxRecord, attempt: int) -> None:
        if record.type != "reminder_notification":
            return
        mark_processing = getattr(self._repository, "mark_scheduled_notification_processing", None)
        append_log = getattr(self._repository, "append_notification_log", None)
        if callable(mark_processing):
            mark_processing(record.alert_id, attempt)
        if callable(append_log):
            from uuid import uuid4

            from care_pilot.features.reminders.domain.models import MessageLogEntry

            append_log(
                MessageLogEntry(
                    id=str(uuid4()),
                    scheduled_notification_id=record.alert_id,
                    reminder_id=str(record.payload.get("reminder_id", "")),
                    user_id=str(record.payload.get("user_id", "")),
                    channel=cast(MessageChannel, record.sink),
                    attempt_number=attempt,
                    event_type="dispatch_started",
                )
            )

    def _sync_reminder_notification_delivered(self, *, record: OutboxRecord, attempt: int) -> None:
        if record.type != "reminder_notification":
            return
        mark_delivered = getattr(self._repository, "mark_scheduled_notification_delivered", None)
        append_log = getattr(self._repository, "append_notification_log", None)
        if callable(mark_delivered):
            mark_delivered(record.alert_id, attempt)
        if callable(append_log):
            from uuid import uuid4

            from care_pilot.features.reminders.domain.models import MessageLogEntry

            append_log(
                MessageLogEntry(
                    id=str(uuid4()),
                    scheduled_notification_id=record.alert_id,
                    reminder_id=str(record.payload.get("reminder_id", "")),
                    user_id=str(record.payload.get("user_id", "")),
                    channel=cast(MessageChannel, record.sink),
                    attempt_number=attempt,
                    event_type="delivered",
                )
            )

    def _sync_reminder_notification_retry(
        self,
        *,
        record: OutboxRecord,
        attempt: int,
        next_attempt_at: datetime,
        error: str,
    ) -> None:
        if record.type != "reminder_notification":
            return
        reschedule = getattr(self._repository, "reschedule_scheduled_notification", None)
        append_log = getattr(self._repository, "append_notification_log", None)
        if callable(reschedule):
            reschedule(
                record.alert_id,
                attempt_count=attempt,
                next_attempt_at=next_attempt_at,
                error=error,
            )
        if callable(append_log):
            from uuid import uuid4

            from care_pilot.features.reminders.domain.models import MessageLogEntry

            append_log(
                MessageLogEntry(
                    id=str(uuid4()),
                    scheduled_notification_id=record.alert_id,
                    reminder_id=str(record.payload.get("reminder_id", "")),
                    user_id=str(record.payload.get("user_id", "")),
                    channel=cast(MessageChannel, record.sink),
                    attempt_number=attempt,
                    event_type="retry_scheduled",
                    error_message=error,
                    metadata={"next_attempt_at": next_attempt_at.isoformat()},
                )
            )

    def _sync_reminder_notification_dead_letter(
        self,
        *,
        record: OutboxRecord,
        attempt: int,
        error: str,
    ) -> None:
        if record.type != "reminder_notification":
            return
        dead_letter = getattr(self._repository, "mark_scheduled_notification_dead_letter", None)
        append_log = getattr(self._repository, "append_notification_log", None)
        if callable(dead_letter):
            dead_letter(record.alert_id, attempt_count=attempt, error=error)
        if callable(append_log):
            from uuid import uuid4

            from care_pilot.features.reminders.domain.models import MessageLogEntry

            append_log(
                MessageLogEntry(
                    id=str(uuid4()),
                    scheduled_notification_id=record.alert_id,
                    reminder_id=str(record.payload.get("reminder_id", "")),
                    user_id=str(record.payload.get("user_id", "")),
                    channel=cast(MessageChannel, record.sink),
                    attempt_number=attempt,
                    event_type="dead_lettered",
                    error_message=error,
                )
            )


__all__ = [
    "AlertPublisher",
    "AlertRepositoryProtocol",
    "EmailSink",
    "InAppSink",
    "OutboxWorker",
    "PushSink",
    "SmsSink",
    "SinkAdapter",
    "TelegramSink",
    "WeChatSink",
    "WhatsAppSink",
]
