"""
backend/routers/chat.py
-----------------------
Thin API layer — all logic lives in ChatAgent.

Endpoints:
    GET    /api/chat/history   - full message history
    DELETE /api/chat/history   - clear history
    POST   /api/chat           - SSE streaming chat response
    POST   /api/chat/audio     - transcribe audio + SSE chat response
"""
from __future__ import annotations

import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.deps import async_client, audio_agent, chat_agent, CHAT_MODEL_ID

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


@router.get("/history")
def get_history():
    return {"messages": chat_agent.memory.all_messages()}


@router.delete("/history")
def clear_history_endpoint():
    chat_agent.clear_history()
    return {"cleared": True}


@router.post("")
async def chat_endpoint(req: ChatRequest):
    """Stream an LLM response via SSE."""
    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="message is required")

    return StreamingResponse(
        chat_agent.stream_async(user_message, async_client, CHAT_MODEL_ID),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/audio")
async def chat_audio(
    audio: UploadFile = File(...),
    backend_name: str = Form("groq"),
):
    """Transcribe uploaded audio (webm/mp3/wav) then stream the LLM response."""
    raw_bytes = await audio.read()
    filename  = audio.filename or "audio.webm"

    try:
        user_message = audio_agent.transcribe_bytes(raw_bytes, filename)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Transcription failed: {exc}")

    if not user_message:
        raise HTTPException(status_code=422, detail="Transcription returned empty text")

    async def _stream():
        yield f"data: {json.dumps({'transcribed': user_message})}\n\n"
        async for chunk in chat_agent.stream_async(user_message, async_client, CHAT_MODEL_ID):
            yield chunk

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
