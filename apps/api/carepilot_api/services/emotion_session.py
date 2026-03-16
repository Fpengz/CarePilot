"""
Session-scoped emotion inference helpers for API routes.

This module adapts the EmotionAgent to HTTP response contracts while
preserving feature-layer boundaries.
"""

from __future__ import annotations

from uuid import uuid4

from apps.api.carepilot_api.deps import EmotionDeps
from apps.api.carepilot_api.errors import build_api_error
from care_pilot.agent.emotion.agent import (
    EmotionAgentDisabledError,
    EmotionSpeechDisabledError,
)
from care_pilot.agent.emotion.schemas import (
    EmotionInferenceResult,
)
from care_pilot.core.contracts.api import (
    EmotionHealthResponse,
    EmotionInferenceResponse,
    EmotionObservationResponse,
    EmotionTextRequest,
)


def _to_observation(
    result: EmotionInferenceResult,
    *,
    request_id: str | None,
    correlation_id: str | None,
) -> EmotionObservationResponse:
    return EmotionObservationResponse(
        source_type=result.source_type,
        final_emotion=result.final_emotion,
        product_state=result.product_state,
        confidence=result.confidence,
        text_branch=result.text_branch,
        speech_branch=result.speech_branch,
        context_features=result.context_features,
        fusion_method=result.fusion_method,
        model_metadata=result.model_metadata,
        trace=result.trace,
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


def infer_text_for_session(
    *,
    deps: EmotionDeps,
    payload: EmotionTextRequest,
    request_id: str | None,
    correlation_id: str | None,
    user_id: str | None,
) -> EmotionInferenceResponse:
    try:
        result = deps.emotion_agent.infer_text(
            text=payload.text,
            language=payload.language,
            user_id=user_id,
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
            "emotion": str(result.final_emotion),
            "product_state": str(result.product_state),
            "confidence": result.confidence,
            "fusion_method": result.fusion_method,
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
        result = deps.emotion_agent.infer_speech(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
            transcription=transcription,
            language=language,
            user_id=user_id,
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
            "emotion": str(result.final_emotion),
            "product_state": str(result.product_state),
            "confidence": result.confidence,
            "fusion_method": result.fusion_method,
        },
    )
    return EmotionInferenceResponse(
        observation=_to_observation(result, request_id=request_id, correlation_id=correlation_id),
    )


def get_emotion_health(*, deps: EmotionDeps) -> EmotionHealthResponse:
    health = deps.emotion_agent.health()
    return EmotionHealthResponse.model_validate(health.model_dump(mode="json"))
