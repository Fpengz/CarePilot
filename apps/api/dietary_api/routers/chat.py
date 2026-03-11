"""API router for companion chat endpoints."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..deps import chat_deps
from ..routes_shared import current_session, get_context, require_action
from dietary_guardian.agent.chat.emotion import EmotionAgent as ChatEmotionAgent

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


@router.get("/api/v1/chat/history")
def chat_history(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> dict[str, object]:
    require_action(session, "chat.messages.read")
    deps = chat_deps(get_context(request))
    return {"messages": deps.chat_agent.memory.all_messages()}


@router.delete("/api/v1/chat/history")
def chat_clear_history(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> dict[str, object]:
    require_action(session, "chat.messages.write")
    deps = chat_deps(get_context(request))
    deps.chat_agent.clear_history()
    return {"cleared": True}


@router.post("/api/v1/chat")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
):
    require_action(session, "chat.messages.write")
    deps = chat_deps(get_context(request))
    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="message is required")

    async def _stream():
        loop = asyncio.get_running_loop()
        emotion_ctx: str | None = None
        try:
            result = await loop.run_in_executor(
                None, deps.emotion_agent.analyze_text, user_message
            )
            emotion_ctx = ChatEmotionAgent.to_context_str(result)
            yield f"data: {json.dumps({'emotion': result.emotion, 'score': result.score})}\n\n"
        except Exception as exc:
            print(f"[chat] Emotion analysis failed: {exc}")

        async for chunk in deps.chat_agent.stream_async(
            user_message, deps.async_client, deps.model_id, emotion_context=emotion_ctx
        ):
            yield chunk

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
    deps = chat_deps(get_context(request))
    raw_bytes = await audio.read()
    filename = audio.filename or "audio.webm"

    try:
        user_message = deps.audio_agent.transcribe_bytes(raw_bytes, filename)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Transcription failed: {exc}")

    if not user_message:
        raise HTTPException(status_code=422, detail="Transcription returned empty text")

    async def _stream():
        yield f"data: {json.dumps({'transcribed': user_message})}\n\n"

        loop = asyncio.get_running_loop()
        emotion_ctx: str | None = None
        try:
            result = await loop.run_in_executor(
                None,
                lambda: deps.emotion_agent.analyze_audio(
                    raw_bytes, filename, transcription=user_message
                ),
            )
            emotion_ctx = ChatEmotionAgent.to_context_str(result)
            yield f"data: {json.dumps({'emotion': result.emotion, 'score': result.score})}\n\n"
        except Exception as exc:
            print(f"[chat/audio] Emotion analysis failed: {exc}")

        async for chunk in deps.chat_agent.stream_async(
            user_message, deps.async_client, deps.model_id, emotion_context=emotion_ctx
        ):
            yield chunk

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
