import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import Protocol

from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.alerting import AlertDeliveryResult, AlertMessage, OutboxRecord
from dietary_guardian.services.channels import TelegramChannel, WeChatChannel, WhatsAppChannel

logger = get_logger(__name__)


class SinkAdapter(Protocol):
    name: str

    def send(self, message: AlertMessage) -> AlertDeliveryResult: ...


class InAppSink:
    name = "in_app"

    def send(self, message: AlertMessage) -> AlertDeliveryResult:
        return AlertDeliveryResult(
            alert_id=message.alert_id,
            sink=self.name,
            success=True,
            attempt=1,
            destination="app://alerts",
            provider_reference="in_app",
        )


class PushSink:
    name = "push"

    def send(self, message: AlertMessage) -> AlertDeliveryResult:
        return AlertDeliveryResult(
            alert_id=message.alert_id,
            sink=self.name,
            success=True,
            attempt=1,
            destination="push://default",
            provider_reference="push",
        )


class TelegramSink:
    name = "telegram"

    def __init__(self) -> None:
        self._channel = TelegramChannel()

    def send(self, message: AlertMessage) -> AlertDeliveryResult:
        proxy = _alert_to_reminder(message)
        result = self._channel.send(proxy)
        return AlertDeliveryResult(
            alert_id=message.alert_id,
            sink=self.name,
            success=result.success,
            attempt=result.attempts,
            destination=result.destination,
            provider_reference="telegram",
            error=result.error,
        )


class WhatsAppSink:
    name = "whatsapp"

    def __init__(self) -> None:
        self._channel = WhatsAppChannel()

    def send(self, message: AlertMessage) -> AlertDeliveryResult:
        proxy = _alert_to_reminder(message)
        result = self._channel.send(proxy)
        return AlertDeliveryResult(
            alert_id=message.alert_id,
            sink=self.name,
            success=result.success,
            attempt=result.attempts,
            destination=result.destination,
            provider_reference="whatsapp",
            error=result.error,
        )


class WeChatSink:
    name = "wechat"

    def __init__(self) -> None:
        self._channel = WeChatChannel()

    def send(self, message: AlertMessage) -> AlertDeliveryResult:
        proxy = _alert_to_reminder(message)
        result = self._channel.send(proxy)
        return AlertDeliveryResult(
            alert_id=message.alert_id,
            sink=self.name,
            success=result.success,
            attempt=result.attempts,
            destination=result.destination,
            provider_reference="wechat",
            error=result.error,
        )


class AlertPublisher:
    def __init__(self, repository: "AlertRepositoryProtocol") -> None:
        self._repository = repository

    def publish(self, message: AlertMessage) -> list[OutboxRecord]:
        logger.info(
            "alert_publish alert_id=%s correlation_id=%s destinations=%s",
            message.alert_id,
            message.correlation_id,
            message.destinations,
        )
        return self._repository.enqueue_alert(message)


class AlertRepositoryProtocol(Protocol):
    def enqueue_alert(self, message: AlertMessage) -> list[OutboxRecord]: ...

    def lease_alert_records(
        self,
        now: datetime,
        lease_owner: str,
        lease_seconds: int,
        limit: int,
        alert_id: str | None = None,
    ) -> list[OutboxRecord]: ...

    def mark_alert_delivered(self, alert_id: str, sink: str, attempt_count: int | None = None) -> None: ...

    def reschedule_alert(self, alert_id: str, sink: str, next_attempt_at: datetime, attempt_count: int, error: str) -> None: ...

    def mark_alert_dead_letter(
        self,
        alert_id: str,
        sink: str,
        error: str,
        attempt_count: int | None = None,
    ) -> None: ...

    def list_alert_records(self, alert_id: str | None = None) -> list[OutboxRecord]: ...


class OutboxWorker:
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
            "telegram": TelegramSink(),
            "whatsapp": WhatsAppSink(),
            "wechat": WeChatSink(),
        }

    async def process_once(self, alert_id: str | None = None) -> list[AlertDeliveryResult]:
        now = datetime.now(timezone.utc)
        leased = self._repository.lease_alert_records(
            now=now,
            lease_owner=self._lease_owner,
            lease_seconds=30,
            limit=self._concurrency,
            alert_id=alert_id,
        )
        if not leased:
            return []

        tasks = [self._deliver_record(record) for record in leased]
        return await asyncio.gather(*tasks)

    async def _deliver_record(self, record: OutboxRecord) -> AlertDeliveryResult:
        sink = self._sinks.get(record.sink)
        if sink is None:
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

        message = AlertMessage(
            alert_id=record.alert_id,
            type=record.type,
            severity=record.severity,
            payload=record.payload,
            destinations=[record.sink],
            correlation_id=record.correlation_id,
            created_at=record.created_at,
        )
        attempt = record.attempt_count + 1
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
            self._repository.mark_alert_delivered(record.alert_id, record.sink, attempt_count=attempt)
            return result.model_copy(update={"attempt": attempt})

        if attempt >= self._max_attempts:
            self._repository.mark_alert_dead_letter(
                record.alert_id,
                record.sink,
                result.error or "delivery failed",
                attempt_count=attempt,
            )
            return result.model_copy(update={"attempt": attempt})

        delay_seconds = (2 ** attempt) + random.randint(0, 2)
        next_attempt = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        self._repository.reschedule_alert(
            alert_id=record.alert_id,
            sink=record.sink,
            next_attempt_at=next_attempt,
            attempt_count=attempt,
            error=result.error or "delivery failed",
        )
        return result.model_copy(update={"attempt": attempt})


def _alert_to_reminder(message: AlertMessage):
    from datetime import datetime

    from dietary_guardian.models.medication import ReminderEvent

    text = message.payload.get("message", "Alert")
    medication_name = message.payload.get("medication_name", text)
    dosage_text = message.payload.get("dosage_text", message.type)
    scheduled_at_raw = message.payload.get("scheduled_at")
    try:
        scheduled_at = datetime.fromisoformat(scheduled_at_raw) if scheduled_at_raw else datetime.now(timezone.utc)
    except ValueError:
        scheduled_at = datetime.now(timezone.utc)
    return ReminderEvent(
        id=f"alert-{message.alert_id}",
        user_id=message.payload.get("user_id", "system"),
        medication_name=medication_name,
        scheduled_at=scheduled_at,
        dosage_text=dosage_text,
    )
