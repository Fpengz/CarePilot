"""
Expose webhook endpoints for external channel integrations.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from care_pilot.features.companion.messaging.normalization import InboundAttachment, InboundMessage
from care_pilot.features.reminders.use_cases.inbound_messages import handle_inbound_message
from care_pilot.platform.app_context import AppContext

from ..deps import get_context

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhooks"])


@router.post("/api/v1/webhooks/telegram")
async def telegram_webhook(
    request: Request, context: AppContext = Depends(get_context)
) -> dict[str, str]:
    """Handle inbound Telegram update payloads."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="invalid json") from e

    message = payload.get("message")
    if not message:
        return {"status": "ignored"}

    chat_id = str(message.get("chat", {}).get("id", ""))
    if not chat_id:
        return {"status": "ignored"}

    text = message.get("text", "")
    photo = message.get("photo")
    attachments = []
    if photo:
        # Telegram photo list has multiple sizes, take the last one (largest)
        largest_photo = photo[-1]
        attachments.append(
            InboundAttachment(type="image", file_id=largest_photo.get("file_id"))
        )

    # Identify user_id by Telegram chat_id (destination)
    user_id = context.stores.reminders.get_user_id_by_channel_destination(
        channel="telegram", destination=chat_id
    )

    if not user_id:
        logger.warning("telegram_webhook_unlinked_chat_id chat_id=%s", chat_id)
        return {"status": "ignored", "reason": "unlinked_chat_id"}

    inbound = InboundMessage(
        user_id=user_id,
        channel="telegram",
        text=text or "",
        attachments=attachments,
        raw_payload=payload,
    )

    await handle_inbound_message(
        context=context,
        user_id=inbound.user_id,
        channel=inbound.channel,
        message_text=inbound.text,
        # TODO: Pass attachments when handle_inbound_message supports InboundAttachment
    )

    return {"status": "ok"}
