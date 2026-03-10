"""Channel transport adapters public API.

Re-exports ``ChannelResult``, ``NotificationChannel``, and all concrete
channel implementations so callers can import from one place.
"""

from dietary_guardian.infrastructure.notifications.channels.base import (
    ChannelResult,
    NotificationChannel,
)
from dietary_guardian.infrastructure.notifications.channels.telegram import TelegramChannel
from dietary_guardian.infrastructure.notifications.channels.wechat import WeChatChannel
from dietary_guardian.infrastructure.notifications.channels.whatsapp import WhatsAppChannel

__all__ = [
    "ChannelResult",
    "NotificationChannel",
    "TelegramChannel",
    "WeChatChannel",
    "WhatsAppChannel",
]
