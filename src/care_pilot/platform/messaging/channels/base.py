"""Channel transport protocol and shared result model.

All concrete channel adapters (Telegram, WhatsApp, WeChat …) must implement
``NotificationChannel`` and return a ``ChannelResult``.

``SinkAdapter`` is the protocol for outbox sink adapters that accept an
``AlertMessage`` and return an ``AlertDeliveryResult``.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel

from care_pilot.features.reminders.domain.models import ReminderEvent

if TYPE_CHECKING:
    from care_pilot.features.safety.domain.alerts import (
        AlertDeliveryResult,
        AlertMessage,
    )


class ChannelResult(BaseModel):
    """Outcome of a single channel delivery attempt."""

    channel: str
    success: bool
    attempts: int = 1
    error: str | None = None
    delivered_at: datetime | None = None
    destination: str | None = None


class NotificationChannel(Protocol):
    """Transport adapter protocol for reminder delivery."""

    name: str

    def send(self, reminder_event: ReminderEvent) -> ChannelResult: ...


class SinkAdapter(Protocol):
    """Transport adapter protocol for outbox alert delivery."""

    name: str

    def send(self, message: "AlertMessage") -> "AlertDeliveryResult": ...


__all__ = ["ChannelResult", "NotificationChannel", "SinkAdapter"]
