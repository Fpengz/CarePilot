"""WeChat channel adapter (stub — wire in WeChat API credentials to activate)."""

from datetime import datetime, timezone

from dietary_guardian.domain.notifications.models import ReminderEvent
from dietary_guardian.infrastructure.notifications.channels.base import ChannelResult
from dietary_guardian.infrastructure.observability import get_logger

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
            delivered_at=datetime.now(timezone.utc),
            destination="wechat://stub",
        )
