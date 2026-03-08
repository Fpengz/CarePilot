"""
backend/routers/chat.py
-----------------------
Thin API layer — all logic lives in ChatAgent.

Endpoints:
    GET    /api/chat/history   - full message history
    DELETE /api/chat/history   - clear history
    POST   /api/chat           - SSE streaming chat response (emotion-aware)
    POST   /api/chat/audio     - transcribe audio + emotion analysis + SSE chat response

Emotion pipeline
~~~~~~~~~~~~~~~~
Audio  → Groq Whisper transcription (main AudioAgent)
       → MERaLiON-AudioLLM speech emotion + DistilRoBERTa on transcription
       → weighted average (60 / 40)  → injected as LLM system context
Text   → DistilRoBERTa only          → injected as LLM system context

SSE events emitted (in order):
    {"transcribed": "..."}           audio path only
    {"emotion": "anxious", "score": 0.82}
    {"text": "token"}  ...
    {"done": true}
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.emotion_agent import EmotionAgent
from backend.deps import async_client, audio_agent, chat_agent, emotion_agent, CHAT_MODEL_ID

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
    """Stream an LLM response via SSE, with DistilRoBERTa emotion context."""
    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="message is required")

    async def _stream():
        # Run text emotion in a thread pool (blocking model inference)
        loop = asyncio.get_event_loop()
        emotion_ctx: str | None = None
        try:
            result = await loop.run_in_executor(
                None, emotion_agent.analyze_text, user_message
            )
            emotion_ctx = EmotionAgent.to_context_str(result)
            yield f"data: {json.dumps({'emotion': result.emotion, 'score': result.score})}\n\n"
        except Exception as exc:
            print(f"[chat] Emotion analysis failed: {exc}")

        async for chunk in chat_agent.stream_async(
            user_message, async_client, CHAT_MODEL_ID, emotion_context=emotion_ctx
        ):
            yield chunk

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/audio")
async def chat_audio(
    audio: UploadFile = File(...),
    backend_name: str = Form("groq"),
):
    """
    Audio pipeline:
      1. Groq Whisper  → transcription
      2. EmotionAgent  → MERaLiON speech emotion + DistilRoBERTa (weighted)
      3. ChatAgent     → streamed LLM reply with emotion context injected
    """
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

        # Emotion analysis (blocking — run in thread pool)
        loop = asyncio.get_event_loop()
        emotion_ctx: str | None = None
        try:
            result = await loop.run_in_executor(
                None,
                lambda: emotion_agent.analyze_audio(
                    raw_bytes, filename, transcription=user_message
                ),
            )
            emotion_ctx = EmotionAgent.to_context_str(result)
            yield f"data: {json.dumps({'emotion': result.emotion, 'score': result.score})}\n\n"
        except Exception as exc:
            print(f"[chat/audio] Emotion analysis failed: {exc}")

        async for chunk in chat_agent.stream_async(
            user_message, async_client, CHAT_MODEL_ID, emotion_context=emotion_ctx
        ):
            yield chunk

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
