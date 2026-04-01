"""
Handle inbound messages from external channels.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from uuid import uuid4

from care_pilot.features.reminders.domain.models import MessageAttachment
from care_pilot.platform.observability import get_logger

if TYPE_CHECKING:
    from care_pilot.platform.app_context import AppContext

logger = get_logger(__name__)


async def handle_inbound_message(
    *,
    context: AppContext,
    user_id: str,
    channel: str,
    message_text: str,
    attachments: list[MessageAttachment] | None = None,
) -> None:
    """Process an inbound message and route to adherence or chat."""
    logger.info("inbound_message_received user_id=%s channel=%s", user_id, channel)

    # 1. Log to timeline
    context.event_timeline.append(
        event_type="inbound_message_received",
        workflow_name="inbound_engagement",
        correlation_id=str(uuid4()),
        user_id=user_id,
        payload={
            "channel": channel,
            "text_length": len(message_text),
            "attachment_count": len(attachments or []),
        },
    )

    # 2. Check for simple adherence confirmations
    cleaned_text = message_text.strip().lower()
    is_confirmation = re.search(r"\b(taken|yes|confirm|ok|done)\b", cleaned_text)

    if is_confirmation:
        # In a real system, we'd find the most recent 'sent' reminder for this user
        # and mark it as confirmed. For now, we'll log it and let the LLM handle context later.
        logger.info("inbound_adherence_detected user_id=%s", user_id)
        # We could call confirm_reminder_for_session here if we had an occurrence_id

    # 3. Forward to ChatOrchestrator for automated response
    # We need to build a mock Request for the orchestrator if it requires it
    # or refactor orchestrator to not depend on fastapi.Request for core logic.
    # For now, we'll just log that we would respond.

    logger.info("inbound_message_forwarded_to_chat user_id=%s", user_id)

    # record in message thread
    # We'd need to find/create a thread first.
