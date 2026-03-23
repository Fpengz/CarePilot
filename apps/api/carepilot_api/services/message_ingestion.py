"""Inbound/outbound message orchestration for message channels."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Request

from care_pilot.features.reminders.domain.models import (
    MessageAttachment,
    MessageEndpoint,
    MessageThread,
    MessageThreadMessage,
    MessageThreadParticipant,
)
from care_pilot.features.safety.domain.alerts import OutboundMessage
from care_pilot.platform.observability import get_logger

from ..deps import chat_deps
from ..services.companion_orchestration import load_companion_inputs

logger = get_logger(__name__)


@dataclass(frozen=True)
class InboundMessagePayload:
    channel: str
    destination: str
    body: str
    attachments: list[MessageAttachment]


def _ensure_request_ids(request: Request) -> tuple[str, str | None]:
    correlation_raw = getattr(request.state, "correlation_id", None)
    if not correlation_raw:
        correlation_raw = str(uuid4())
        request.state.correlation_id = correlation_raw
    request_raw = getattr(request.state, "request_id", None)
    return str(correlation_raw), (str(request_raw) if request_raw is not None else None)


def ensure_message_thread(
    *,
    context,
    endpoint: MessageEndpoint,
) -> MessageThread:
    thread = context.stores.reminders.get_message_thread(
        user_id=endpoint.user_id,
        channel=endpoint.channel,
        endpoint_id=endpoint.id,
    )
    if thread is not None:
        return thread
    now = datetime.now(UTC)
    thread = MessageThread(
        id=str(uuid4()),
        user_id=endpoint.user_id,
        channel=endpoint.channel,
        endpoint_id=endpoint.id,
        status="active",
        created_at=now,
        updated_at=now,
    )
    context.stores.reminders.create_message_thread(thread)
    context.stores.reminders.add_message_thread_participant(
        MessageThreadParticipant(
            id=str(uuid4()),
            thread_id=thread.id,
            participant_type="user",
            participant_id=endpoint.user_id,
            created_at=now,
        )
    )
    context.stores.reminders.add_message_thread_participant(
        MessageThreadParticipant(
            id=str(uuid4()),
            thread_id=thread.id,
            participant_type="assistant",
            participant_id="assistant",
            created_at=now,
        )
    )
    return thread


def record_thread_message(
    *,
    context,
    thread: MessageThread,
    direction: str,
    body: str,
    attachments: list[MessageAttachment],
    metadata: dict[str, object] | None = None,
) -> MessageThreadMessage:
    message = MessageThreadMessage(
        id=str(uuid4()),
        thread_id=thread.id,
        user_id=thread.user_id,
        channel=thread.channel,
        direction=direction,
        body=body,
        attachments=attachments,
        metadata=metadata or {},
        created_at=datetime.now(UTC),
    )
    return context.stores.reminders.append_message_thread_message(message)


def enqueue_outbound_message(
    *,
    context,
    endpoint: MessageEndpoint,
    thread: MessageThread,
    body: str,
    attachments: list[MessageAttachment],
    correlation_id: str,
) -> None:
    message = OutboundMessage(
        alert_id=str(uuid4()),
        type="message",
        severity="info",
        payload={
            "body": body,
            "destination": endpoint.destination,
            "thread_id": thread.id,
            "channel": endpoint.channel,
            "user_id": endpoint.user_id,
        },
        destinations=[endpoint.channel],
        correlation_id=correlation_id,
        attachments=[attachment.model_dump() for attachment in attachments],
    )
    context.stores.reminders.enqueue_alert(message)


def send_welcome_message(
    *,
    context,
    endpoint: MessageEndpoint,
    thread: MessageThread,
    correlation_id: str,
) -> None:
    welcome_text = (
        "Welcome to CarePilot. You can chat here anytime, including photos of meals."
    )
    record_thread_message(
        context=context,
        thread=thread,
        direction="outbound",
        body=welcome_text,
        attachments=[],
        metadata={"reason": "welcome"},
    )
    enqueue_outbound_message(
        context=context,
        endpoint=endpoint,
        thread=thread,
        body=welcome_text,
        attachments=[],
        correlation_id=correlation_id,
    )
    try:
        context.event_timeline.append(
            event_type="message_welcome_sent",
            workflow_name="message_channels",
            correlation_id=correlation_id,
            request_id=None,
            user_id=endpoint.user_id,
            payload={"channel": endpoint.channel, "endpoint_id": endpoint.id},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("message_welcome_timeline_failed endpoint_id=%s error=%s", endpoint.id, exc)


async def run_inbound_chat(
    *,
    request: Request,
    context,
    thread: MessageThread,
    user_message: str,
) -> str:
    correlation_id, request_id = _ensure_request_ids(request)
    session = {
        "user_id": thread.user_id,
        "session_id": thread.id,
        "profile_mode": "self",
    }
    deps = chat_deps(context, session)
    inputs = await load_companion_inputs(context=context, session=session)
    response_text = ""
    async for event in deps.chat_agent.stream_events(
        user_message=user_message,
        request=request,
        session=session,
        ctx=context,
        inputs=inputs,
    ):
        if event.event == "token":
            response_text += str(event.data.get("text") or "")
    if not response_text.strip():
        response_text = "Thanks for the update. I’m here whenever you need me."
    try:
        context.event_timeline.append(
            event_type="message_inbound_processed",
            workflow_name="message_channels",
            correlation_id=correlation_id,
            request_id=request_id,
            user_id=thread.user_id,
            payload={"thread_id": thread.id, "response_length": len(response_text)},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("message_inbound_timeline_failed thread_id=%s error=%s", thread.id, exc)
    return response_text


async def handle_inbound_message(
    *,
    request: Request,
    context,
    payload: InboundMessagePayload,
) -> dict[str, object]:
    endpoint = context.stores.reminders.get_message_endpoint_by_destination(
        channel=payload.channel,
        destination=payload.destination,
    )
    if endpoint is None and payload.channel == "telegram" and not payload.destination.startswith(
        "telegram://"
    ):
        endpoint = context.stores.reminders.get_message_endpoint_by_destination(
            channel="telegram",
            destination=f"telegram://{payload.destination}",
        )
    if endpoint is None:
        return {"status": "ignored", "reason": "unknown_endpoint"}

    thread = ensure_message_thread(context=context, endpoint=endpoint)
    record_thread_message(
        context=context,
        thread=thread,
        direction="inbound",
        body=payload.body,
        attachments=payload.attachments,
        metadata={"source": payload.channel},
    )

    response_text = await run_inbound_chat(
        request=request,
        context=context,
        thread=thread,
        user_message=payload.body,
    )
    record_thread_message(
        context=context,
        thread=thread,
        direction="outbound",
        body=response_text,
        attachments=[],
        metadata={"source": "chat"},
    )
    correlation_id, _ = _ensure_request_ids(request)
    enqueue_outbound_message(
        context=context,
        endpoint=endpoint,
        thread=thread,
        body=response_text,
        attachments=[],
        correlation_id=correlation_id,
    )
    return {"status": "ok", "thread_id": thread.id}
