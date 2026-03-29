"""Canonical messaging platform exports."""

from care_pilot.platform.messaging.alert_outbox import AlertPublisher, OutboxWorker
from care_pilot.platform.messaging.message_composer import (
    CHANNEL_CAPABILITIES,
    ChannelCapability,
    compose_alert_message,
    format_alert_text_for_transport,
)

__all__ = [
    "AlertPublisher",
    "CHANNEL_CAPABILITIES",
    "ChannelCapability",
    "OutboxWorker",
    "compose_alert_message",
    "format_alert_text_for_transport",
]
