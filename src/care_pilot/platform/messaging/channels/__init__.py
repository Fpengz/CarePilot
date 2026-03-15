"""Channel transport adapters public API.

Re-exports protocols, result models, and all concrete channel/sink
implementations so callers can import from one place.
"""

from care_pilot.platform.messaging.channels.base import (
    ChannelResult,
    NotificationChannel,
    SinkAdapter,
)
from care_pilot.platform.messaging.channels.sinks import (
    EmailSink,
    InAppSink,
    PushSink,
    SmsSink,
    TelegramSink,
    WeChatSink,
    WhatsAppSink,
)
from care_pilot.platform.messaging.channels.telegram import TelegramChannel
from care_pilot.platform.messaging.channels.wechat import WeChatChannel
from care_pilot.platform.messaging.channels.whatsapp import WhatsAppChannel

__all__ = [
    "ChannelResult",
    "EmailSink",
    "InAppSink",
    "NotificationChannel",
    "PushSink",
    "SinkAdapter",
    "SmsSink",
    "TelegramChannel",
    "TelegramSink",
    "WeChatChannel",
    "WeChatSink",
    "WhatsAppChannel",
    "WhatsAppSink",
]
