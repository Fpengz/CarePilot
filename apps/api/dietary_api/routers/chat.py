"""
Expose companion chat API endpoints.

This router defines chat interaction routes and delegates to companion
services for orchestration and policy enforcement.
"""

from __future__ import annotations

import asyncio
import json
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..deps import chat_deps, meal_deps
from ..routes_shared import current_session, get_context, require_action
from dietary_guardian.features.companion.core.health.emotion import EmotionInferenceResult
from dietary_guardian.agent.emotion import EmotionAgentDisabledError, EmotionSpeechDisabledError
from dietary_guardian.features.meals.use_cases import log_meal_from_text

router = APIRouter(tags=["chat"])

_MEAL_PREFIX_RE = re.compile(r"^(?:log\s+meal|meal)\s*:\s*(.+)$", re.IGNORECASE)


def _format_emotion_context(inference: EmotionInferenceResult) -> str:
    pct = int(inference.score * 100)
    return (
        f"[Emotional context] The user appears to be feeling **{inference.emotion}** "
        f"(confidence {pct} %). Please respond with appropriate empathy and tailor "
        f"your advice to their current emotional state."
    )


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


def _parse_meal_command(message: str) -> str | None:
    cleaned = message.strip()
    if not cleaned:
        return None
    if cleaned.lower().startswith("[meal]"):
        remainder = cleaned[6:].strip()
        return remainder or None
    match = _MEAL_PREFIX_RE.match(cleaned)
    if match:
        candidate = match.group(1).strip()
        return candidate or None
    return None


def _log_meal_command(
    *,
    user_id: str,
    meal_text: str,
    stores: object,
    locale: str = "en-SG",
) -> dict[str, object]:
    result = log_meal_from_text(
        user_id=user_id,
        meal_text=meal_text,
        food_store=stores.foods,
        meals_store=stores.meals,
        locale=locale,
    )
    return {
        "event_id": result.validated_event.event_id,
        "meal_name": result.validated_event.meal_name,
        "message": f"Logged meal: {meal_text.strip()}.",
    }


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
    meal_text = _parse_meal_command(user_message)
    if meal_text:
        user_id = str(session.get("user_id", ""))
        meal_result = _log_meal_command(user_id=user_id, meal_text=meal_text, stores=meal_deps(ctx).stores)
        deps.chat_agent.memory.add_message("user", user_message)
        deps.chat_agent.memory.add_message("assistant", meal_result["message"])

        async def _stream():
            yield _format_event("meal_logged", meal_result)
            yield _format_event("token", {"text": meal_result["message"]})
            yield _format_event("done", {"status": "meal_logged"})

        return StreamingResponse(
            _stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    async def _stream():
        loop = asyncio.get_running_loop()
        emotion_ctx: str | None = None
        try:
            inference = await loop.run_in_executor(
                None, lambda: deps.emotion_agent.infer_text(text=user_message)
            )
            emotion_ctx = _format_emotion_context(inference)
            yield _format_event("emotion", {"emotion": inference.emotion, "score": inference.score})
        except EmotionAgentDisabledError:
            # Emotion inference disabled; skip emitting error events.
            pass
        except Exception as exc:  # noqa: BLE001
            yield _format_event("error", {"message": str(exc), "phase": "emotion", "retryable": False})

        async for chunk in deps.chat_agent.stream(
            user_message=user_message,
            emotion_context=emotion_ctx,
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
    ctx = get_context(request)
    deps = chat_deps(ctx, session)
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
        yield _format_event("transcribed", {"text": user_message})
        meal_text = _parse_meal_command(user_message)
        if meal_text:
            user_id = str(session.get("user_id", ""))
            meal_result = _log_meal_command(user_id=user_id, meal_text=meal_text, stores=meal_deps(ctx).stores)
            deps.chat_agent.memory.add_message("user", user_message)
            deps.chat_agent.memory.add_message("assistant", meal_result["message"])
            yield _format_event("meal_logged", meal_result)
            yield _format_event("token", {"text": meal_result["message"]})
            yield _format_event("done", {"status": "meal_logged"})
            return

        loop = asyncio.get_running_loop()
        emotion_ctx: str | None = None
        try:
            inference = await loop.run_in_executor(
                None,
                lambda: deps.emotion_agent.infer_speech(
                    audio_bytes=raw_bytes,
                    filename=filename,
                    transcription=user_message,
                ),
            )
            emotion_ctx = _format_emotion_context(inference)
            yield _format_event("emotion", {"emotion": inference.emotion, "score": inference.score})
        except (EmotionAgentDisabledError, EmotionSpeechDisabledError):
            pass
        except Exception as exc:  # noqa: BLE001
            yield _format_event("error", {"message": str(exc), "phase": "emotion", "retryable": False})

        async for chunk in deps.chat_agent.stream(
            user_message=user_message,
            emotion_context=emotion_ctx,
        ):
            yield chunk

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _format_event(event: str, data: dict) -> str:
    payload = {"event": event, "data": data}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
