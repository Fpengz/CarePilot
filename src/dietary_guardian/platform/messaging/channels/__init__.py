"""Channel transport adapters public API.

Re-exports ``ChannelResult``, ``NotificationChannel``, and all concrete
channel implementations so callers can import from one place.
"""

from dietary_guardian.platform.messaging.channels.base import (
    ChannelResult,
    NotificationChannel,
)
from dietary_guardian.platform.messaging.channels.telegram import TelegramChannel
from dietary_guardian.platform.messaging.channels.wechat import WeChatChannel
from dietary_guardian.platform.messaging.channels.whatsapp import WhatsAppChannel

__all__ = [
    "ChannelResult",
    "NotificationChannel",
    "TelegramChannel",
    "WeChatChannel",
    "WhatsAppChannel",
]
