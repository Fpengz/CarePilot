import asyncio
import json
import random
import smtplib
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Protocol, cast

from dietary_guardian.config.settings import get_settings
from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.alerting import AlertDeliveryResult, AlertMessage, OutboxRecord
from dietary_guardian.models.reminder_notifications import ReminderNotificationChannel
from dietary_guardian.services.message_composer import compose_alert_message, format_alert_text_for_transport
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


class EmailSink:
    name = "email"

    def send(self, message: AlertMessage) -> AlertDeliveryResult:
        settings = get_settings()
        destination = str(message.payload.get("destination", "")).strip() or "mailto://default"
        if settings.channels.email_dev_mode:
            logger.info("email_sink_dev_send alert_id=%s destination=%s", message.alert_id, destination)
            return AlertDeliveryResult(
                alert_id=message.alert_id,
                sink=self.name,
                success=True,
                attempt=1,
                destination=destination,
                provider_reference="email-dev",
            )
        if not destination:
            return AlertDeliveryResult(
                alert_id=message.alert_id,
                sink=self.name,
                success=False,
                attempt=1,
                error="missing email destination",
            )
        if not settings.channels.email_smtp_host:
            return AlertDeliveryResult(
                alert_id=message.alert_id,
                sink=self.name,
                success=False,
                attempt=1,
                error="email smtp host not configured",
            )
        composed = compose_alert_message(message, channel=self.name)
        body = format_alert_text_for_transport(composed)
        smtp = smtplib.SMTP(settings.channels.email_smtp_host, settings.channels.email_smtp_port, timeout=10)
        try:
            if settings.channels.email_smtp_use_tls:
                smtp.starttls()
            if settings.channels.email_smtp_username and settings.channels.email_smtp_password:
                smtp.login(settings.channels.email_smtp_username, settings.channels.email_smtp_password)
            smtp.sendmail(
                settings.channels.email_from_address,
                [destination],
                f"Subject: {composed.title}\nTo: {destination}\nFrom: {settings.channels.email_from_address}\n\n{body}",
            )
        finally:
            smtp.quit()
        return AlertDeliveryResult(
            alert_id=message.alert_id,
            sink=self.name,
            success=True,
            attempt=1,
            destination=destination,
            provider_reference="smtp",
        )


class SmsSink:
    name = "sms"

    def send(self, message: AlertMessage) -> AlertDeliveryResult:
        settings = get_settings()
        destination = str(message.payload.get("destination", "")).strip()
        if settings.channels.sms_dev_mode:
            logger.info("sms_sink_dev_send alert_id=%s destination=%s", message.alert_id, destination or "sms://default")
            return AlertDeliveryResult(
                alert_id=message.alert_id,
                sink=self.name,
                success=True,
                attempt=1,
                destination=destination or "sms://default",
                provider_reference="sms-dev",
            )
        if not destination:
            return AlertDeliveryResult(
                alert_id=message.alert_id,
                sink=self.name,
                success=False,
                attempt=1,
                error="missing sms destination",
            )
        if not settings.channels.sms_webhook_url:
            return AlertDeliveryResult(
                alert_id=message.alert_id,
                sink=self.name,
                success=False,
                attempt=1,
                error="sms webhook url not configured",
            )
        composed = compose_alert_message(message, channel=self.name)
        payload = json.dumps(
            {
                "to": destination,
                "from": settings.channels.sms_sender_id,
                "message": format_alert_text_for_transport(composed),
                "alert_id": message.alert_id,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            str(settings.channels.sms_webhook_url),
            data=payload,
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {settings.channels.sms_api_key}"} if settings.channels.sms_api_key else {}),
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            status_code = getattr(response, "status", 200)
        if status_code >= 400:
            return AlertDeliveryResult(
                alert_id=message.alert_id,
                sink=self.name,
                success=False,
                attempt=1,
                destination=destination,
                error=f"sms provider returned {status_code}",
            )
        return AlertDeliveryResult(
            alert_id=message.alert_id,
            sink=self.name,
            success=True,
            attempt=1,
            destination=destination,
            provider_reference="sms-webhook",
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
            "email": EmailSink(),
            "sms": SmsSink(),
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
        self._sync_reminder_notification_processing(record=record, attempt=attempt)
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
            self._sync_reminder_notification_delivered(record=record, attempt=attempt)
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
            return result.model_copy(update={"attempt": attempt})

        delay_seconds = (2 ** attempt) + random.randint(0, 2)
        next_attempt = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
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
        return result.model_copy(update={"attempt": attempt})

    def _sync_reminder_notification_processing(self, *, record: OutboxRecord, attempt: int) -> None:
        if record.type != "reminder_notification":
            return
        mark_processing = getattr(self._repository, "mark_scheduled_notification_processing", None)
        append_log = getattr(self._repository, "append_notification_log", None)
        if callable(mark_processing):
            mark_processing(record.alert_id, attempt)
        if callable(append_log):
            from uuid import uuid4

            from dietary_guardian.models.reminder_notifications import ReminderNotificationLogEntry

            append_log(
                ReminderNotificationLogEntry(
                    id=str(uuid4()),
                    scheduled_notification_id=record.alert_id,
                    reminder_id=str(record.payload.get("reminder_id", "")),
                    user_id=str(record.payload.get("user_id", "")),
                    channel=cast(ReminderNotificationChannel, record.sink),
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

            from dietary_guardian.models.reminder_notifications import ReminderNotificationLogEntry

            append_log(
                ReminderNotificationLogEntry(
                    id=str(uuid4()),
                    scheduled_notification_id=record.alert_id,
                    reminder_id=str(record.payload.get("reminder_id", "")),
                    user_id=str(record.payload.get("user_id", "")),
                    channel=cast(ReminderNotificationChannel, record.sink),
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
            reschedule(record.alert_id, attempt_count=attempt, next_attempt_at=next_attempt_at, error=error)
        if callable(append_log):
            from uuid import uuid4

            from dietary_guardian.models.reminder_notifications import ReminderNotificationLogEntry

            append_log(
                ReminderNotificationLogEntry(
                    id=str(uuid4()),
                    scheduled_notification_id=record.alert_id,
                    reminder_id=str(record.payload.get("reminder_id", "")),
                    user_id=str(record.payload.get("user_id", "")),
                    channel=cast(ReminderNotificationChannel, record.sink),
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

            from dietary_guardian.models.reminder_notifications import ReminderNotificationLogEntry

            append_log(
                ReminderNotificationLogEntry(
                    id=str(uuid4()),
                    scheduled_notification_id=record.alert_id,
                    reminder_id=str(record.payload.get("reminder_id", "")),
                    user_id=str(record.payload.get("user_id", "")),
                    channel=cast(ReminderNotificationChannel, record.sink),
                    attempt_number=attempt,
                    event_type="dead_lettered",
                    error_message=error,
                )
            )


def _alert_to_reminder(message: AlertMessage):
    from datetime import datetime

    from dietary_guardian.models.medication import ReminderEvent

    composed = compose_alert_message(message, channel=message.destinations[0] if message.destinations else "unknown")
    medication_name = message.payload.get("medication_name", composed.title)
    dosage_text = message.payload.get("dosage_text", format_alert_text_for_transport(composed))
    scheduled_at_raw = message.payload.get("scheduled_at")
    try:
        scheduled_at = datetime.fromisoformat(scheduled_at_raw) if scheduled_at_raw else message.created_at
    except ValueError:
        scheduled_at = message.created_at
    return ReminderEvent(
        id=f"alert-{message.alert_id}",
        user_id=message.payload.get("user_id", "system"),
        medication_name=medication_name,
        scheduled_at=scheduled_at,
        dosage_text=dosage_text,
    )
