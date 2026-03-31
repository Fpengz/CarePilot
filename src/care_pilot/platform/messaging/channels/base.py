"""Channel transport protocol and shared result model.

All concrete channel adapters (Telegram, WhatsApp, WeChat …) must implement
``NotificationChannel`` and return a ``ChannelResult``.

``SinkAdapter`` is the protocol for outbox sink adapters that accept an
``OutboundMessage`` and return an ``AlertDeliveryResult``.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel

from care_pilot.features.safety.domain.alerts import OutboundMessage

if TYPE_CHECKING:
    from care_pilot.features.safety.domain.alerts import AlertDeliveryResult, OutboundMessage


class ChannelResult(BaseModel):
    """Outcome of a single channel delivery attempt."""

    channel: str
    success: bool
    attempts: int = 1
    error: str | None = None
    delivered_at: datetime | None = None
    destination: str | None = None


class NotificationChannel(Protocol):
    """Transport adapter protocol for message delivery."""

    name: str

    def send(self, message: OutboundMessage) -> ChannelResult: ...


class SinkAdapter(Protocol):
    """Transport adapter protocol for outbox alert delivery."""

    name: str

    def send(self, message: "OutboundMessage") -> "AlertDeliveryResult": ...


__all__ = ["ChannelResult", "NotificationChannel", "SinkAdapter"]
