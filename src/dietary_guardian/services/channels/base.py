from datetime import datetime
from typing import Protocol

from pydantic import BaseModel

from dietary_guardian.models.medication import ReminderEvent


class ChannelResult(BaseModel):
    channel: str
    success: bool
    attempts: int = 1
    error: str | None = None
    delivered_at: datetime | None = None
    destination: str | None = None


class NotificationChannel(Protocol):
    name: str

    def send(self, reminder_event: ReminderEvent) -> ChannelResult: ...
