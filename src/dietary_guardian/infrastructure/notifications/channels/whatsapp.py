"""WhatsApp channel adapter (stub — wire in Twilio/Meta credentials to activate)."""

from datetime import datetime, timezone

from dietary_guardian.domain.notifications.models import ReminderEvent
from dietary_guardian.infrastructure.notifications.channels.base import ChannelResult
from dietary_guardian.infrastructure.observability import get_logger

logger = get_logger(__name__)


class WhatsAppChannel:
    name = "whatsapp"

    def send(self, reminder_event: ReminderEvent) -> ChannelResult:
        # Adapter placeholder for provider integration (Twilio/Meta API)
        logger.info(
            "whatsapp_send_stub event_id=%s medication=%s",
            reminder_event.id,
            reminder_event.medication_name,
        )
        return ChannelResult(
            channel=self.name,
            success=True,
            delivered_at=datetime.now(timezone.utc),
            destination="whatsapp://stub",
        )
