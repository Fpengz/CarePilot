"""Inbound message channel endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from care_pilot.features.reminders.domain.models import MessageAttachment

from ..routes_shared import get_context
from ..services.message_ingestion import InboundMessagePayload, handle_inbound_message

router = APIRouter(tags=["messages"])


@router.post("/api/v1/messages/inbound")
async def inbound_message(payload: dict[str, object], request: Request) -> dict[str, object]:
    channel = str(payload.get("channel", "")).strip()
    destination = str(payload.get("destination", "")).strip()
    body = str(payload.get("body") or payload.get("text") or "").strip()
    attachments_raw = payload.get("attachments") or []
    attachments = []
    if isinstance(attachments_raw, list):
        attachments = [MessageAttachment.model_validate(item) for item in attachments_raw]
    context = get_context(request)
    result = await handle_inbound_message(
        request=request,
        context=context,
        payload=InboundMessagePayload(
            channel=channel,
            destination=destination,
            body=body or "Sent an attachment.",
            attachments=attachments,
        ),
    )
    return result


@router.post("/api/v1/messages/inbound/telegram")
async def inbound_telegram(request: Request) -> dict[str, object]:
    payload = await request.json()
    message = payload.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "").strip()
    if not chat_id:
        return {"status": "ignored", "reason": "missing_chat_id"}
    text = str(message.get("text") or "").strip()
    photos = message.get("photo") or []
    attachments = []
    if isinstance(photos, list) and photos:
        largest = photos[-1]
        file_id = str(largest.get("file_id") or "")
        if file_id:
            attachments.append(
                MessageAttachment(
                    attachment_type="image",
                    url=file_id,
                    mime_type="image/jpeg",
                    caption=text or None,
                    size_bytes=int(largest.get("file_size") or 0) or None,
                )
            )
    body = text or ("Sent an image." if attachments else "")
    context = get_context(request)
    result = await handle_inbound_message(
        request=request,
        context=context,
        payload=InboundMessagePayload(
            channel="telegram",
            destination=chat_id,
            body=body,
            attachments=attachments,
        ),
    )
    return result
