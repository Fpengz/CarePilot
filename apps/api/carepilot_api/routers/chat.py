"""
Expose companion chat API endpoints.

This router defines chat interaction routes and delegates to companion
services for orchestration and policy enforcement.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Literal, Mapping, TypedDict, cast
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..deps import AppContext, chat_deps, meal_deps
from ..routes_shared import current_session, get_context, require_action
from care_pilot.agent.emotion.schemas import EmotionInferenceResult
from care_pilot.agent.emotion import (
    EmotionAgentDisabledError,
    EmotionSpeechDisabledError,
)
from care_pilot.features.meals.use_cases import log_meal_from_text
from care_pilot.features.companion.core.snapshot import build_case_snapshot
from care_pilot.features.companion.core.context_loader import (
    load_companion_inputs,
)
from care_pilot.platform.persistence import AppStores
from care_pilot.features.companion.chat.meal_intent import (
    classify_meal_log_intent,
    heuristic_meal_log_intent,
    meal_proposal_cache_key,
)
from care_pilot.features.companion.chat.memory_store import (
    build_memory_context,
    fetch_memory_snippets,
    record_chat_turn,
)
from care_pilot.features.companion.core.chat_context import format_chat_context
from care_pilot.agent.runtime.chat_runtime import ChatStreamRuntime
from care_pilot.platform.observability import get_logger

router = APIRouter(tags=["chat"])
logger = get_logger(__name__)

_MEAL_PREFIX_RE = re.compile(r"^(?:log\s+meal|meal)\s*:\s*(.+)$", re.IGNORECASE)


def _format_emotion_context(inference: EmotionInferenceResult) -> str:
    pct = int(inference.confidence * 100)
    return (
        f"[Emotional context] The user appears to be feeling **{inference.final_emotion}** "
        f"(confidence {pct} %). Please respond with appropriate empathy and tailor "
        f"your advice to their current emotional state."
    )


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class MealConfirmRequest(BaseModel):
    proposal_id: str
    action: Literal["confirm", "skip"]


class MealLogResult(TypedDict):
    event_id: str
    meal_name: str
    message: str


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


def _meal_proposal_prompt(meal_text: str) -> str:
    return f"I can log **{meal_text}** as a meal. Would you like me to save it?"


def _build_extra_context(ctx: AppContext, session: dict[str, object]) -> str:
    inputs = load_companion_inputs(context=ctx, session=session)
    snapshot = build_case_snapshot(
        user_profile=inputs.user_profile,
        health_profile=inputs.health_profile,
        meals=inputs.meals,
        reminders=inputs.reminders,
        adherence_events=inputs.adherence_events,
        symptoms=inputs.symptoms,
        biomarker_readings=inputs.biomarker_readings,
        clinical_snapshot=inputs.clinical_snapshot,
    )
    return format_chat_context(
        snapshot=snapshot,
        recent_meals=inputs.meals,
        health_profile=inputs.health_profile,
        tool_specs=ctx.tool_registry.list_specs(),
        recent_events=ctx.event_timeline.get_events(user_id=str(session.get("user_id"))),
    )


def _merge_context(base: str, memory_context: str | None) -> str:
    if not memory_context:
        return base
    if base:
        return f"{base}\n\n{memory_context}"
    return memory_context


def _log_suppressed_emotion_failure(
    *,
    request: Request,
    phase: Literal["emotion", "speech_emotion"],
    exc: Exception,
) -> None:
    logger.warning(
        "chat_emotion_inference_suppressed phase=%s request_id=%s correlation_id=%s error=%s",
        phase,
        getattr(request.state, "request_id", None),
        getattr(request.state, "correlation_id", None),
        exc,
    )


async def _collect_chat_followup(
    *,
    runtime: ChatStreamRuntime,
    user_message: str,
    extra_context: str | None,
    emotion_context: str | None = None,
    response_prefix: str | None = None,
) -> str:
    messages: list[dict[str, object]] = []
    if extra_context:
        messages.append({"role": "system", "content": extra_context})
    if emotion_context:
        messages.append({"role": "system", "content": emotion_context})
    messages.append({"role": "user", "content": user_message})

    response = response_prefix or ""
    async for token in runtime.stream(messages=messages):
        response += token
    return response


def _log_meal_command(
    *,
    user_id: str,
    meal_text: str,
    stores: AppStores,
    locale: str = "en-SG",
) -> MealLogResult:
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

    async def _stream():
        loop = asyncio.get_running_loop()
        emotion_ctx: str | None = None
        if deps.emotion_agent.inference_enabled:
            try:
                inference = await loop.run_in_executor(
                    None,
                    lambda: deps.emotion_agent.infer_text(text=user_message),
                )
                logger.info(
                    "chat_emotion_inference_result request_id=%s emotion=%s confidence=%s product_state=%s",
                    getattr(request.state, "request_id", None),
                    inference.final_emotion,
                    inference.confidence,
                    inference.product_state,
                )
                emotion_ctx = _format_emotion_context(inference)
                yield _format_event(
                    "emotion",
                    {
                        "emotion": inference.final_emotion,
                        "score": inference.confidence,
                        "product_state": inference.product_state,
                    },
                )
            except EmotionAgentDisabledError:
                # Emotion inference disabled; skip emitting error events.
                pass
            except Exception as exc:  # noqa: BLE001
                _log_suppressed_emotion_failure(request=request, phase="emotion", exc=exc)

        if not meal_text:
            intent_result, needs_llm = heuristic_meal_log_intent(user_message)
            if needs_llm:
                intent_result = await classify_meal_log_intent(
                    user_message, engine=ctx.chat_inference_engine
                )
            if intent_result.intent and intent_result.meal_text:
                user_id = str(session.get("user_id", ""))
                session_id = str(session.get("session_id", ""))
                proposal_id = str(uuid4())
                cache_key = meal_proposal_cache_key(
                    user_id=user_id,
                    session_id=session_id,
                    proposal_id=proposal_id,
                )
                ctx.cache_store.set_json(
                    cache_key,
                    {
                        "proposal_id": proposal_id,
                        "user_id": user_id,
                        "session_id": session_id,
                        "meal_text": intent_result.meal_text,
                        "reason": intent_result.reason,
                    },
                    ttl_seconds=600,
                )
                deps.chat_agent.memory.add_message("user", user_message)
                prompt = _meal_proposal_prompt(intent_result.meal_text)
                deps.chat_agent.memory.add_message("assistant", prompt)
                yield _format_event(
                    "meal_proposed",
                    {
                        "proposal_id": proposal_id,
                        "meal_text": intent_result.meal_text,
                        "prompt": prompt,
                        "reason": intent_result.reason,
                    },
                )
                yield _format_event("done", {"status": "meal_proposed"})
                return

        system_context = _build_extra_context(ctx, session)
        memory_context = None
        if ctx.memory_store.enabled:
            snippets = await fetch_memory_snippets(
                memory_store=ctx.memory_store,
                user_id=str(session.get("user_id", "")),
                query=user_message,
                limit=ctx.settings.memory.top_k,
            )
            if snippets:
                memory_context = build_memory_context(snippets)
        user_prompt = user_message
        if memory_context:
            user_prompt = f"{user_message}\n\n{memory_context}"
        response_prefix = None
        if meal_text:
            user_id = str(session.get("user_id", ""))
            meal_result = _log_meal_command(
                user_id=user_id,
                meal_text=meal_text,
                stores=meal_deps(ctx).stores,
            )
            response_prefix = f"{meal_result['message']}\n\n"
            yield _format_event("meal_logged", cast(dict[str, object], meal_result))

        assistant_response = ""
        had_error = False
        if response_prefix:
            assistant_response += response_prefix
            yield _format_event("token", {"text": response_prefix})

        messages: list[dict[str, object]] = []
        if system_context:
            messages.append({"role": "system", "content": system_context})
        if emotion_ctx:
            messages.append({"role": "system", "content": emotion_ctx})
        messages.append({"role": "user", "content": user_prompt})

        try:
            logger.info(
                "chat_stream_start request_id=%s",
                getattr(request.state, "request_id", None),
            )
            async for token in ctx.chat_stream_runtime.stream(messages=messages):
                assistant_response += token
                yield _format_event("token", {"text": token})
            logger.info(
                "chat_stream_complete request_id=%s tokens_len=%d",
                getattr(request.state, "request_id", None),
                len(assistant_response),
            )
        except Exception as exc:  # noqa: BLE001
            had_error = True
            yield _format_event(
                "error",
                {"message": str(exc), "phase": "stream", "retryable": False},
            )
        yield _format_event("done", {"status": "complete"})
        if assistant_response and not had_error:
            await record_chat_turn(
                memory_store=ctx.memory_store,
                user_id=str(session.get("user_id", "")),
                session_id=str(session.get("session_id", "")),
                user_message=user_message,
                assistant_message=assistant_response,
                metadata={"source": "chat"},
            )

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

        loop = asyncio.get_running_loop()
        emotion_ctx: str | None = None
        if deps.emotion_agent.inference_enabled and deps.emotion_agent.speech_enabled:
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
                yield _format_event(
                    "emotion",
                    {
                        "emotion": inference.final_emotion,
                        "score": inference.confidence,
                        "product_state": inference.product_state,
                    },
                )
            except (EmotionAgentDisabledError, EmotionSpeechDisabledError):
                pass
            except Exception as exc:  # noqa: BLE001
                _log_suppressed_emotion_failure(request=request, phase="speech_emotion", exc=exc)

        if not meal_text:
            intent_result, needs_llm = heuristic_meal_log_intent(user_message)
            if needs_llm:
                intent_result = await classify_meal_log_intent(
                    user_message, engine=ctx.chat_inference_engine
                )
            if intent_result.intent and intent_result.meal_text:
                user_id = str(session.get("user_id", ""))
                session_id = str(session.get("session_id", ""))
                proposal_id = str(uuid4())
                cache_key = meal_proposal_cache_key(
                    user_id=user_id,
                    session_id=session_id,
                    proposal_id=proposal_id,
                )
                ctx.cache_store.set_json(
                    cache_key,
                    {
                        "proposal_id": proposal_id,
                        "user_id": user_id,
                        "session_id": session_id,
                        "meal_text": intent_result.meal_text,
                        "reason": intent_result.reason,
                    },
                    ttl_seconds=600,
                )
                deps.chat_agent.memory.add_message("user", user_message)
                prompt = _meal_proposal_prompt(intent_result.meal_text)
                deps.chat_agent.memory.add_message("assistant", prompt)
                yield _format_event(
                    "meal_proposed",
                    {
                        "proposal_id": proposal_id,
                        "meal_text": intent_result.meal_text,
                        "prompt": prompt,
                        "reason": intent_result.reason,
                    },
                )
                yield _format_event("done", {"status": "meal_proposed"})
                return

        extra_context = _build_extra_context(ctx, session)
        memory_context = None
        if ctx.memory_store.enabled:
            snippets = await fetch_memory_snippets(
                memory_store=ctx.memory_store,
                user_id=str(session.get("user_id", "")),
                query=user_message,
                limit=ctx.settings.memory.top_k,
            )
            if snippets:
                memory_context = build_memory_context(snippets)
        extra_context = _merge_context(extra_context, memory_context)
        response_prefix = None
        if meal_text:
            user_id = str(session.get("user_id", ""))
            meal_result = _log_meal_command(
                user_id=user_id,
                meal_text=meal_text,
                stores=meal_deps(ctx).stores,
            )
            response_prefix = f"{meal_result['message']}\n\n"
            yield _format_event("meal_logged", cast(dict[str, object], meal_result))

        assistant_response = ""
        had_error = False
        async for event in deps.chat_agent.stream_events(
            user_message=user_message,
            emotion_context=emotion_ctx,
            extra_context=extra_context,
            response_prefix=response_prefix,
        ):
            if event.event == "token":
                assistant_response += event.data.get("text", "")
            if event.event == "error":
                had_error = True
            yield _format_event(event.event, event.data)
        if assistant_response and not had_error:
            await record_chat_turn(
                memory_store=ctx.memory_store,
                user_id=str(session.get("user_id", "")),
                session_id=str(session.get("session_id", "")),
                user_message=user_message,
                assistant_message=assistant_response,
                metadata={"source": "chat_audio"},
            )

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
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
    user_id = str(session.get("user_id", ""))
    session_id = str(session.get("session_id", ""))
    cache_key = meal_proposal_cache_key(
        user_id=user_id,
        session_id=session_id,
        proposal_id=payload.proposal_id,
    )
    proposal = ctx.cache_store.get_json(cache_key)
    if proposal is None:
        raise HTTPException(status_code=404, detail="meal proposal not found")
    if payload.action == "skip":
        ctx.cache_store.delete(cache_key)
        return {"status": "skipped"}
    if (
        str(proposal.get("user_id", "")) != user_id
        or str(proposal.get("session_id", "")) != session_id
    ):
        raise HTTPException(status_code=403, detail="meal proposal not valid for this session")
    meal_text = str(proposal.get("meal_text", "")).strip()
    if not meal_text:
        raise HTTPException(status_code=400, detail="meal proposal missing meal_text")
    meal_result = _log_meal_command(
        user_id=user_id, meal_text=meal_text, stores=meal_deps(ctx).stores
    )
    extra_context = _build_extra_context(ctx, session)
    memory_context = None
    if ctx.memory_store.enabled:
        snippets = await fetch_memory_snippets(
            memory_store=ctx.memory_store,
            user_id=user_id,
            query=meal_text,
            limit=ctx.settings.memory.top_k,
        )
        if snippets:
            memory_context = build_memory_context(snippets)
    extra_context = _merge_context(extra_context, memory_context)
    confirm_message = f"I confirmed logging this meal: {meal_text}."
    response_prefix = f"{meal_result['message']}\n\n"
    assistant_response = await _collect_chat_followup(
        runtime=ctx.chat_stream_runtime,
        user_message=confirm_message,
        extra_context=extra_context,
        response_prefix=response_prefix,
    )
    display_response = assistant_response
    if display_response.startswith(meal_result["message"]):
        display_response = display_response[len(meal_result["message"]) :].lstrip()
    if assistant_response:
        await record_chat_turn(
            memory_store=ctx.memory_store,
            user_id=user_id,
            session_id=session_id,
            user_message=confirm_message,
            assistant_message=assistant_response,
            metadata={"source": "chat_confirm"},
        )
    ctx.cache_store.delete(cache_key)
    return {
        "status": "logged",
        "meal_name": meal_result["meal_name"],
        "message": meal_result["message"],
        "event_id": meal_result["event_id"],
        "assistant_followup": display_response,
    }


def _format_event(event: str, data: Mapping[str, object]) -> str:
    payload = {"event": event, "data": dict(data)}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
