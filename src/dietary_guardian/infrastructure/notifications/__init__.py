"""Infrastructure notifications package.

Houses channel transport adapters, message formatting, and the alert outbox
delivery worker.  These are concrete integration concerns and must not be
imported by domain or application-layer modules.
"""

from dietary_guardian.infrastructure.notifications.alert_outbox import (
    AlertPublisher,
    OutboxWorker,
)
from dietary_guardian.infrastructure.notifications.message_composer import (
    CHANNEL_CAPABILITIES,
    ChannelCapability,
    compose_alert_message,
    format_alert_text_for_transport,
)

__all__ = [
    "AlertPublisher",
    "ChannelCapability",
    "CHANNEL_CAPABILITIES",
    "OutboxWorker",
    "compose_alert_message",
    "format_alert_text_for_transport",
]
