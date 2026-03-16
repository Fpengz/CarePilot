"""
Provide a WeChat reminder notification adapter stub.

This module defines the WeChat channel adapter placeholder for future wiring.
"""

from datetime import UTC, datetime

from care_pilot.features.reminders.domain.models import ReminderEvent
from care_pilot.platform.messaging.channels.base import ChannelResult
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


class WeChatChannel:
    name = "wechat"

    def send(self, reminder_event: ReminderEvent) -> ChannelResult:
        # Adapter placeholder for WeChat API integration.
        logger.info(
            "wechat_send_stub event_id=%s medication=%s",
            reminder_event.id,
            reminder_event.medication_name,
        )
        return ChannelResult(
            channel=self.name,
            success=True,
            delivered_at=datetime.now(UTC),
            destination="wechat://stub",
        )
