"""
Expose the canonical emotion agent facade.

This module provides the emotion agent used by application workflows,
wrapping the inference runtime port.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Callable, TypeVar

from dietary_guardian.agent.emotion.schemas import (
    EmotionSpeechAgentInput,
    EmotionTextAgentInput,
    EmotionContextFeatures,
    EmotionRuntimeHealth,
    EmotionInferenceResult,
)
from dietary_guardian.features.companion.emotion.ports import EmotionInferencePort

T = TypeVar("T")


class EmotionInferenceTimeoutError(RuntimeError):
    """Raised when inference exceeds configured wall-clock time."""


class EmotionAgentDisabledError(RuntimeError):
    """Raised when emotion inference is disabled via feature flag."""


class EmotionSpeechDisabledError(RuntimeError):
    """Raised when speech emotion inference is disabled via feature flag."""


def _run_with_timeout(action: Callable[[], T], timeout_seconds: float) -> T:
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(action)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError as exc:
            raise EmotionInferenceTimeoutError("emotion inference timed out") from exc


def infer_text_emotion(
    *,
    port: EmotionInferencePort,
    payload: EmotionTextAgentInput,
    timeout_seconds: float,
) -> EmotionInferenceResult:
    return _run_with_timeout(lambda: port.infer_text(payload), timeout_seconds)


def infer_speech_emotion(
    *,
    port: EmotionInferencePort,
    payload: EmotionSpeechAgentInput,
    timeout_seconds: float,
) -> EmotionInferenceResult:
    return _run_with_timeout(lambda: port.infer_speech(payload), timeout_seconds)


class EmotionAgent:
    """Canonical agent facade for text and speech emotion inference."""

    name = "emotion_agent"

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
        context: EmotionContextFeatures | None = None,
    ):
        if not self._inference_enabled:
            raise EmotionAgentDisabledError("emotion inference is disabled")
        return infer_text_emotion(
            port=self._runtime,
            payload=EmotionTextAgentInput(text=text, language=language, context=context),
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
        context: EmotionContextFeatures | None = None,
    ):
        if not self._inference_enabled:
            raise EmotionAgentDisabledError("emotion inference is disabled")
        if not self._speech_enabled:
            raise EmotionSpeechDisabledError("speech emotion inference is disabled")
        return infer_speech_emotion(
            port=self._runtime,
            payload=EmotionSpeechAgentInput(
                audio_bytes=audio_bytes,
                filename=filename,
                content_type=content_type,
                transcription=transcription,
                language=language,
                context=context,
            ),
            timeout_seconds=self._request_timeout_seconds,
        )

    @property
    def inference_enabled(self) -> bool:
        return self._inference_enabled

    @property
    def speech_enabled(self) -> bool:
        return self._speech_enabled

    def health(self) -> EmotionRuntimeHealth:
        health = self._runtime.health()
        if not self._inference_enabled:
            return EmotionRuntimeHealth(
                status="disabled",
                model_cache_ready=False,
                source_commit=health.source_commit,
                detail="emotion inference disabled",
            )
        if self._speech_enabled:
            return health
        return EmotionRuntimeHealth(
            status=health.status,
            model_cache_ready=health.model_cache_ready,
            source_commit=health.source_commit,
            detail="speech emotion inference disabled",
        )

    @property
    def timeout_error_type(self) -> type[EmotionInferenceTimeoutError]:
        return EmotionInferenceTimeoutError
