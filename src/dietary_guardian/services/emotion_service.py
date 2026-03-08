from __future__ import annotations

from dietary_guardian.application.emotion.ports import EmotionInferencePort, SpeechEmotionInput, TextEmotionInput
from dietary_guardian.application.emotion.use_cases import (
    EmotionInferenceTimeoutError,
    infer_speech_emotion,
    infer_text_emotion,
)
from dietary_guardian.models.emotion import EmotionInferenceResult, EmotionRuntimeHealth


class EmotionServiceDisabledError(RuntimeError):
    """Raised when emotion inference is disabled via feature flag."""


class EmotionSpeechDisabledError(RuntimeError):
    """Raised when speech emotion inference is disabled via feature flag."""


class EmotionService:
    def __init__(
        self,
        *,
        runtime: EmotionInferencePort,
        inference_enabled: bool,
        speech_enabled: bool,
        request_timeout_seconds: float,
    ) -> None:
        self._runtime = runtime
        self._inference_enabled = inference_enabled
        self._speech_enabled = speech_enabled
        self._request_timeout_seconds = request_timeout_seconds

    def infer_text(
        self,
        *,
        text: str,
        language: str | None = None,
    ) -> EmotionInferenceResult:
        if not self._inference_enabled:
            raise EmotionServiceDisabledError("emotion inference is disabled")
        return infer_text_emotion(
            port=self._runtime,
            payload=TextEmotionInput(text=text, language=language),
            timeout_seconds=self._request_timeout_seconds,
        )

    def infer_speech(
        self,
        *,
        audio_bytes: bytes,
        filename: str | None = None,
        content_type: str | None = None,
        transcription: str | None = None,
        language: str | None = None,
    ) -> EmotionInferenceResult:
        if not self._inference_enabled:
            raise EmotionServiceDisabledError("emotion inference is disabled")
        if not self._speech_enabled:
            raise EmotionSpeechDisabledError("speech emotion inference is disabled")
        return infer_speech_emotion(
            port=self._runtime,
            payload=SpeechEmotionInput(
                audio_bytes=audio_bytes,
                filename=filename,
                content_type=content_type,
                transcription=transcription,
                language=language,
            ),
            timeout_seconds=self._request_timeout_seconds,
        )

    def health(self) -> EmotionRuntimeHealth:
        return self._runtime.health()

    @property
    def timeout_error_type(self) -> type[EmotionInferenceTimeoutError]:
        return EmotionInferenceTimeoutError

