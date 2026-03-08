from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from ..deps import emotion_deps
from ..routes_shared import current_session, get_context, require_action
from ..schemas.emotions import (
    CompatEmotionResponse,
    CompatEmotionTextRequest,
    EmotionHealthResponse,
    EmotionInferenceResponse,
    EmotionTextRequest,
)
from ..services.emotions import (
    get_compat_emotion_health,
    get_emotion_health,
    infer_compat_speech_for_session,
    infer_compat_text_for_session,
    infer_speech_for_session,
    infer_text_for_session,
)

router = APIRouter(tags=["emotions"])


@router.get("/api/v1/emotions/health", response_model=EmotionHealthResponse)
def emotions_health(request: Request) -> EmotionHealthResponse:
    return get_emotion_health(deps=emotion_deps(get_context(request)))


@router.post("/api/v1/emotions/text", response_model=EmotionInferenceResponse)
def emotions_text(
    payload: EmotionTextRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> EmotionInferenceResponse:
    require_action(session, "emotions.text.infer")
    return infer_text_for_session(
        deps=emotion_deps(get_context(request)),
        payload=payload,
        request_id=getattr(request.state, "request_id", None),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/api/v1/emotions/speech", response_model=EmotionInferenceResponse)
async def emotions_speech(
    request: Request,
    file: UploadFile = File(...),
    transcription: str | None = Form(default=None),
    language: str | None = Form(default=None),
    session: dict[str, object] = Depends(current_session),
) -> EmotionInferenceResponse:
    require_action(session, "emotions.speech.infer")
    audio_bytes = await file.read()
    return infer_speech_for_session(
        deps=emotion_deps(get_context(request)),
        audio_bytes=audio_bytes,
        filename=file.filename,
        content_type=file.content_type,
        transcription=transcription,
        language=language,
        request_id=getattr(request.state, "request_id", None),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/emotion/health", response_model=EmotionHealthResponse)
def emotions_compat_health(request: Request) -> EmotionHealthResponse:
    return get_compat_emotion_health(deps=emotion_deps(get_context(request)))


@router.post("/emotion/text", response_model=CompatEmotionResponse)
def emotions_compat_text(
    payload: CompatEmotionTextRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> CompatEmotionResponse:
    require_action(session, "emotions.text.infer")
    return infer_compat_text_for_session(
        deps=emotion_deps(get_context(request)),
        payload=payload,
    )


@router.post("/emotion/speech", response_model=CompatEmotionResponse)
async def emotions_compat_speech(
    request: Request,
    file: UploadFile = File(...),
    transcription: str | None = Form(default=None),
    session: dict[str, object] = Depends(current_session),
) -> CompatEmotionResponse:
    require_action(session, "emotions.speech.infer")
    audio_bytes = await file.read()
    return infer_compat_speech_for_session(
        deps=emotion_deps(get_context(request)),
        audio_bytes=audio_bytes,
        filename=file.filename,
        content_type=file.content_type,
        transcription=transcription,
    )
