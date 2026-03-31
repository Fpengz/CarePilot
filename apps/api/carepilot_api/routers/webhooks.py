"""
Expose webhook endpoints for external channel integrations.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

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

    # Identify user_id by Telegram chat_id (destination)
    user_id = context.stores.reminders.get_user_id_by_channel_destination(
        channel="telegram", destination=chat_id
    )

    if not user_id:
        logger.warning("telegram_webhook_unlinked_chat_id chat_id=%s", chat_id)
        return {"status": "ignored", "reason": "unlinked_chat_id"}

    await handle_inbound_message(
        context=context, user_id=user_id, channel="telegram", message_text=text
    )

    return {"status": "ok"}
