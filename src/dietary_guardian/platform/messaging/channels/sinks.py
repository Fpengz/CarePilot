"""Concrete outbox sink adapter implementations.

Each class implements the ``SinkAdapter`` protocol and maps a named delivery
channel (``in_app``, ``push``, ``email``, ``sms``, ``telegram``, ``whatsapp``,
``wechat``) to its transport backend.  Thin adapters (Telegram / WhatsApp /
WeChat) delegate to the corresponding ``NotificationChannel`` implementation in
this package; heavier adapters (email, SMS) own their own transport logic.
"""

from __future__ import annotations

import json
import smtplib
import urllib.request

from dietary_guardian.config.app import get_settings
from dietary_guardian.features.safety.domain.alerts import AlertDeliveryResult, AlertMessage
from dietary_guardian.platform.messaging.channels.telegram import TelegramChannel
from dietary_guardian.platform.messaging.channels.wechat import WeChatChannel
from dietary_guardian.platform.messaging.channels.whatsapp import WhatsAppChannel
from dietary_guardian.platform.messaging.message_composer import (
    compose_alert_message,
    format_alert_text_for_transport,
)
from dietary_guardian.platform.observability import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _alert_to_reminder(message: AlertMessage):
    """Adapt an ``AlertMessage`` to a ``ReminderEvent`` for channel sinks."""
    from datetime import datetime

    from dietary_guardian.features.reminders.domain.models import ReminderEvent

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


# ---------------------------------------------------------------------------
# Concrete sink adapters
# ---------------------------------------------------------------------------


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
        req = urllib.request.Request(
            str(settings.channels.sms_webhook_url),
            data=payload,
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {settings.channels.sms_api_key}"} if settings.channels.sms_api_key else {}),
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as response:  # noqa: S310
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
        destination = str(message.payload.get("destination", "")).strip() or None
        result = self._channel.send(proxy, destination=destination)
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


__all__ = [
    "EmailSink",
    "InAppSink",
    "PushSink",
    "SmsSink",
    "TelegramSink",
    "WeChatSink",
    "WhatsAppSink",
    "_alert_to_reminder",
]
