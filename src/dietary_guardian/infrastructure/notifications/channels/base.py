"""Channel transport protocol and shared result model.

All concrete channel adapters (Telegram, WhatsApp, WeChat …) must implement
``NotificationChannel`` and return a ``ChannelResult``.
"""

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel

from dietary_guardian.domain.notifications.models import ReminderEvent


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


__all__ = ["ChannelResult", "NotificationChannel"]
