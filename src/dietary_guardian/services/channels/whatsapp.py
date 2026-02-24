from datetime import datetime, timezone

from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.medication import ReminderEvent
from dietary_guardian.services.channels.base import ChannelResult

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
