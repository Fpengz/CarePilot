"""
Session-scoped emotion inference helpers for API routes.

This module adapts the EmotionAgent to HTTP response contracts while
preserving feature-layer boundaries.
"""

from __future__ import annotations

from apps.api.dietary_api.deps import EmotionDeps
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    EmotionHealthResponse,
    EmotionInferenceResponse,
    EmotionObservationResponse,
    EmotionTextRequest,
)
from dietary_guardian.agent.emotion import (
    EmotionAgentDisabledError,
    EmotionSpeechDisabledError,
)
from dietary_guardian.agent.emotion.schemas import (
    EmotionContextFeatures,
    EmotionInferenceResult,
    EmotionLabel,
)
from uuid import uuid4


def _to_observation(
    result: EmotionInferenceResult,
    *,
    request_id: str | None,
    correlation_id: str | None,
) -> EmotionObservationResponse:
    return EmotionObservationResponse(
        source_type=result.source_type,
        text_branch=result.text_branch,
        speech_branch=result.speech_branch,
        context_features=result.context_features,
        fusion=result.fusion,
        created_at=result.created_at,
        request_id=request_id,
        correlation_id=correlation_id,
    )


def _map_inference_error(exc: Exception, *, deps: EmotionDeps) -> Exception:
    if isinstance(exc, EmotionAgentDisabledError):
        return build_api_error(
            status_code=503,
            code="emotions.disabled",
            message="emotion inference is disabled",
        )
    if isinstance(exc, EmotionSpeechDisabledError):
        return build_api_error(
            status_code=503,
            code="emotions.speech_disabled",
            message="speech emotion inference is disabled",
        )
    if isinstance(exc, ValueError) and "fusion model not configured" in str(exc):
        return build_api_error(
            status_code=503,
            code="emotions.not_configured",
            message="emotion fusion model not configured",
        )
    if isinstance(exc, deps.emotion_agent.timeout_error_type):
        return build_api_error(
            status_code=504,
            code="emotions.timeout",
            message="emotion inference timed out",
        )
    if isinstance(exc, ValueError):
        return build_api_error(
            status_code=400,
            code="emotions.invalid_input",
            message=str(exc),
        )
    return exc

def _build_context_features(*, deps: EmotionDeps, user_id: str | None) -> EmotionContextFeatures:
    if not user_id:
        return EmotionContextFeatures(recent_labels=[], trend="stable")
    history = [
        event
        for event in deps.event_timeline.get_events(user_id=user_id)
        if event.event_type == "emotion_observed"
    ]
    history = sorted(history, key=lambda e: e.created_at)
    window = deps.settings.emotion.history_window
    recent = history[-window:]
    recent_labels: list[EmotionLabel] = []
    for event in recent:
        raw = str(event.payload.get("emotion", "")).lower()
        try:
            recent_labels.append(EmotionLabel(raw))
        except ValueError:
            continue
    trend = "stable"
    negative = {
        EmotionLabel.SAD,
        EmotionLabel.ANGRY,
        EmotionLabel.FRUSTRATED,
        EmotionLabel.ANXIOUS,
        EmotionLabel.FEARFUL,
        EmotionLabel.CONFUSED,
    }
    if len(recent_labels) >= 2:
        prev, last = recent_labels[-2], recent_labels[-1]
        if last in negative and prev not in negative:
            trend = "worsening"
        elif last not in negative and prev in negative:
            trend = "improving"
    return EmotionContextFeatures(recent_labels=recent_labels, trend=trend)

def infer_text_for_session(
    *,
    deps: EmotionDeps,
    payload: EmotionTextRequest,
    request_id: str | None,
    correlation_id: str | None,
    user_id: str | None,
) -> EmotionInferenceResponse:
    try:
        context = _build_context_features(deps=deps, user_id=user_id)
        result = deps.emotion_agent.infer_text(
            text=payload.text,
            language=payload.language,
            context=context,
        )
    except Exception as exc:
        raise _map_inference_error(exc, deps=deps)
    deps.event_timeline.append(
        event_type="emotion_observed",
        workflow_name="emotion_inference",
        request_id=request_id,
        correlation_id=correlation_id or str(uuid4()),
        user_id=user_id,
        payload={
            "emotion": str(result.fusion.emotion_label),
            "product_state": str(result.fusion.product_state),
        },
    )
    return EmotionInferenceResponse(
        observation=_to_observation(result, request_id=request_id, correlation_id=correlation_id),
    )


def infer_speech_for_session(
    *,
    deps: EmotionDeps,
    audio_bytes: bytes,
    filename: str | None,
    content_type: str | None,
    transcription: str | None,
    language: str | None,
    request_id: str | None,
    correlation_id: str | None,
    user_id: str | None,
) -> EmotionInferenceResponse:
    try:
        context = _build_context_features(deps=deps, user_id=user_id)
        result = deps.emotion_agent.infer_speech(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
            transcription=transcription,
            language=language,
            context=context,
        )
    except Exception as exc:
        raise _map_inference_error(exc, deps=deps)
    deps.event_timeline.append(
        event_type="emotion_observed",
        workflow_name="emotion_inference",
        request_id=request_id,
        correlation_id=correlation_id or str(uuid4()),
        user_id=user_id,
        payload={
            "emotion": str(result.fusion.emotion_label),
            "product_state": str(result.fusion.product_state),
        },
    )
    return EmotionInferenceResponse(
        observation=_to_observation(result, request_id=request_id, correlation_id=correlation_id),
    )


def get_emotion_health(*, deps: EmotionDeps) -> EmotionHealthResponse:
    health = deps.emotion_agent.health()
    return EmotionHealthResponse.model_validate(health.model_dump(mode="json"))
