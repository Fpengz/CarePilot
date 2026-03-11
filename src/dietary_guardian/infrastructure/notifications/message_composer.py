"""Message formatting for alert and reminder notification delivery.

Produces a ``PresentationMessage`` from an ``AlertMessage``, respecting
per-channel capabilities.  Transport adapters call
``format_alert_text_for_transport`` to get a plain string ready for the wire.
"""

from pydantic import BaseModel

from dietary_guardian.domain.alerts.models import AlertMessage
from dietary_guardian.application.contracts.agent_envelopes import PresentationMessage


class ChannelCapability(BaseModel):
    channel: str
    supports_text: bool = True
    supports_images: bool = False
    supports_buttons: bool = False
    max_chars: int = 4096
    rate_limit_hint: str | None = None


CHANNEL_CAPABILITIES: dict[str, ChannelCapability] = {
    "in_app": ChannelCapability(channel="in_app", supports_images=True, supports_buttons=True, max_chars=8000),
    "push": ChannelCapability(channel="push", supports_images=False, supports_buttons=False, max_chars=256),
    "telegram": ChannelCapability(channel="telegram", supports_images=True, supports_buttons=True, max_chars=4096),
    "whatsapp": ChannelCapability(channel="whatsapp", supports_images=True, supports_buttons=False, max_chars=4096),
    "wechat": ChannelCapability(channel="wechat", supports_images=True, supports_buttons=True, max_chars=4096),
}


def compose_alert_message(alert: AlertMessage, *, channel: str) -> PresentationMessage:
    """Build a ``PresentationMessage`` from an alert, tailored to the target channel."""
    payload_message = alert.payload.get("message", "Alert")
    title = "Alert Notification"
    if alert.type == "medication_reminder":
        title = "Medication Reminder"
    elif alert.type.endswith("_alert"):
        title = "Alert Notification"

    body = payload_message
    if alert.type == "medication_reminder":
        medication = alert.payload.get("medication_name", "Medication")
        dosage = alert.payload.get("dosage_text", "")
        scheduled_at = alert.payload.get("scheduled_at")
        body = f"{medication} {dosage}".strip()
        if scheduled_at:
            body = f"{body} at {scheduled_at}"

    return PresentationMessage(
        channel=channel,
        title=title,
        body=body,
        severity=alert.severity,
        metadata={"alert_type": alert.type, "alert_id": alert.alert_id},
    )


def format_alert_text_for_transport(message: PresentationMessage) -> str:
    """Render a ``PresentationMessage`` to a plain transport string."""
    # Transport adapters remain dumb: they only deliver rendered channel text.
    return f"{message.title}: {message.body}"


__all__ = [
    "ChannelCapability",
    "CHANNEL_CAPABILITIES",
    "compose_alert_message",
    "format_alert_text_for_transport",
]
