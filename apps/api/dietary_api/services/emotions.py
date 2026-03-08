from __future__ import annotations

from apps.api.dietary_api.deps import EmotionDeps
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas.emotions import (
    CompatEmotionResponse,
    CompatEmotionTextRequest,
    EmotionEvidenceResponse,
    EmotionHealthResponse,
    EmotionInferenceResponse,
    EmotionObservationResponse,
    EmotionTextRequest,
)
from dietary_guardian.infrastructure.emotion import to_compat_response
from dietary_guardian.models.emotion import EmotionInferenceResult
from dietary_guardian.services.emotion_service import (
    EmotionServiceDisabledError,
    EmotionSpeechDisabledError,
)


def _to_observation(
    result: EmotionInferenceResult,
    *,
    request_id: str | None,
    correlation_id: str | None,
) -> EmotionObservationResponse:
    return EmotionObservationResponse(
        source_type=result.source_type,
        emotion=result.emotion,
        score=result.score,
        confidence_band=result.confidence_band,
        model_name=result.model_name,
        model_version=result.model_version,
        evidence=[EmotionEvidenceResponse(label=item.label, score=item.score) for item in result.evidence],
        transcription=result.transcription,
        created_at=result.created_at,
        request_id=request_id,
        correlation_id=correlation_id,
    )


def _map_inference_error(exc: Exception, *, deps: EmotionDeps) -> Exception:
    if isinstance(exc, EmotionServiceDisabledError):
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
    if isinstance(exc, deps.emotion_service.timeout_error_type):
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
) -> EmotionInferenceResponse:
    try:
        result = deps.emotion_service.infer_text(text=payload.text, language=payload.language)
    except Exception as exc:
        raise _map_inference_error(exc, deps=deps)
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
) -> EmotionInferenceResponse:
    try:
        result = deps.emotion_service.infer_speech(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
            transcription=transcription,
            language=language,
        )
    except Exception as exc:
        raise _map_inference_error(exc, deps=deps)
    return EmotionInferenceResponse(
        observation=_to_observation(result, request_id=request_id, correlation_id=correlation_id),
    )


def get_emotion_health(*, deps: EmotionDeps) -> EmotionHealthResponse:
    health = deps.emotion_service.health()
    return EmotionHealthResponse.model_validate(health.model_dump(mode="json"))


def _ensure_compat_enabled(*, deps: EmotionDeps) -> None:
    if not deps.settings.emotion_compat_routes_enabled:
        raise build_api_error(
            status_code=404,
            code="emotions.compat_route_disabled",
            message="emotion compatibility routes are disabled",
        )


def infer_compat_text_for_session(
    *,
    deps: EmotionDeps,
    payload: CompatEmotionTextRequest,
) -> CompatEmotionResponse:
    _ensure_compat_enabled(deps=deps)
    try:
        result = deps.emotion_service.infer_text(text=payload.text)
    except Exception as exc:
        raise _map_inference_error(exc, deps=deps)
    return CompatEmotionResponse.model_validate(to_compat_response(result))


def infer_compat_speech_for_session(
    *,
    deps: EmotionDeps,
    audio_bytes: bytes,
    filename: str | None,
    content_type: str | None,
    transcription: str | None,
) -> CompatEmotionResponse:
    _ensure_compat_enabled(deps=deps)
    try:
        result = deps.emotion_service.infer_speech(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
            transcription=transcription,
        )
    except Exception as exc:
        raise _map_inference_error(exc, deps=deps)
    return CompatEmotionResponse.model_validate(to_compat_response(result))


def get_compat_emotion_health(*, deps: EmotionDeps) -> EmotionHealthResponse:
    _ensure_compat_enabled(deps=deps)
    return get_emotion_health(deps=deps)
