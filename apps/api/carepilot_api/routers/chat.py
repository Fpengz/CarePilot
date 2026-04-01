"""
Expose companion chat API endpoints.

This router defines chat interaction routes and delegates to companion
services for orchestration and policy enforcement.
"""

from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from care_pilot.platform.observability import get_logger

from ..deps import chat_deps
from ..routes_shared import current_session, get_context, require_action

router = APIRouter(tags=["chat"])
logger = get_logger(__name__)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class MealConfirmRequest(BaseModel):
    proposal_id: str
    action: Literal["confirm", "skip"]


@router.get("/api/v1/chat/history")
def chat_history(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> dict[str, object]:
    require_action(session, "chat.messages.read")
    deps = chat_deps(get_context(request), session)
    return {"messages": deps.chat_agent.memory.all_messages()}


@router.delete("/api/v1/chat/history")
def chat_clear_history(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> dict[str, object]:
    require_action(session, "chat.messages.write")
    deps = chat_deps(get_context(request), session)
    deps.chat_agent.clear_history()
    return {"cleared": True}


@router.post("/api/v1/chat")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
):
    require_action(session, "chat.messages.write")
    ctx = get_context(request)
    deps = chat_deps(ctx, session)
    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="message is required")

    from ..services.companion_orchestration import load_companion_inputs

    inputs = await load_companion_inputs(context=ctx, session=session)

    async def _stream():
        async for event in deps.chat_agent.stream_events(
            user_message=user_message,
            request=request,
            session=session,
            ctx=ctx,
            inputs=inputs,
        ):
            payload_data = {"event": event.event, "data": dict(event.data)}
            yield f"data: {json.dumps(payload_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/v1/chat/audio")
async def chat_audio(
    request: Request,
    audio: UploadFile = File(...),
    backend_name: str = Form("groq"),
    session: dict[str, object] = Depends(current_session),
):
    del backend_name
    require_action(session, "chat.messages.write")
    ctx = get_context(request)
    deps = chat_deps(ctx, session)
    raw_bytes = await audio.read()
    filename = audio.filename or "audio.webm"

    from ..services.companion_orchestration import load_companion_inputs

    inputs = await load_companion_inputs(context=ctx, session=session)

    async def _stream():
        async for event in deps.chat_agent.stream_audio_events(
            audio_bytes=raw_bytes,
            filename=filename,
            content_type=audio.content_type,
            request=request,
            session=session,
            ctx=ctx,
            inputs=inputs,
        ):
            payload_data = {"event": event.event, "data": dict(event.data)}
            yield f"data: {json.dumps(payload_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text-event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/v1/chat/meal/confirm")
async def confirm_meal_log(
    payload: MealConfirmRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> dict[str, object]:
    require_action(session, "chat.messages.write")
    ctx = get_context(request)
    deps = chat_deps(ctx, session)

    from ..services.companion_orchestration import load_companion_inputs

    inputs = await load_companion_inputs(context=ctx, session=session)

    result = await deps.chat_agent.confirm_meal_log(
        proposal_id=payload.proposal_id,
        action=payload.action,
        request=request,
        session=session,
        ctx=ctx,
        inputs=inputs,
    )
    return result
