"""
Expose the canonical emotion agent facade.

This module provides the emotion agent used by application workflows,
wrapping the inference runtime port.
"""

from __future__ import annotations

import asyncio
from typing import TypeVar

from care_pilot.agent.emotion.schemas import (
    EmotionInferenceResult,
    EmotionRuntimeHealth,
    EmotionSpeechAgentInput,
    EmotionTextAgentInput,
)
from care_pilot.features.companion.emotion.ports import EmotionInferencePort
from care_pilot.platform.runtime.concurrency_guards import (
    get_emotion_speech_semaphore,
    get_emotion_text_semaphore,
)

T = TypeVar("T")


class EmotionInferenceTimeoutError(RuntimeError):
    """Raised when inference exceeds configured wall-clock time."""


class EmotionAgentDisabledError(RuntimeError):
    """Raised when emotion inference is disabled via feature flag."""


class EmotionSpeechDisabledError(RuntimeError):
    """Raised when speech emotion inference is disabled via feature flag."""


async def infer_text_emotion(
    *,
    port: EmotionInferencePort,
    payload: EmotionTextAgentInput,
    timeout_seconds: float,
) -> EmotionInferenceResult:
    try:
        # Apply backpressure/concurrency guard
        async with get_emotion_text_semaphore():
            return await asyncio.wait_for(
                port.infer_text(payload),
                timeout=timeout_seconds,
            )
    except TimeoutError as exc:
        raise EmotionInferenceTimeoutError("emotion inference timed out") from exc


async def infer_speech_emotion(
    *,
    port: EmotionInferencePort,
    payload: EmotionSpeechAgentInput,
    timeout_seconds: float,
) -> EmotionInferenceResult:
    try:
        # Apply backpressure/concurrency guard
        async with get_emotion_speech_semaphore():
            return await asyncio.wait_for(
                port.infer_speech(payload),
                timeout=timeout_seconds,
            )
    except TimeoutError as exc:
        raise EmotionInferenceTimeoutError("emotion inference timed out") from exc


class EmotionAgent:
    """Canonical agent facade for text and speech emotion inference."""

    name = "emotion_agent"
    timeout_error_type = EmotionInferenceTimeoutError

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

    async def infer_text(
        self,
        *,
        text: str,
        language: str | None = None,
        user_id: str | None = None,
    ):
        if not self._inference_enabled:
            raise EmotionAgentDisabledError("emotion inference is disabled")
        return await infer_text_emotion(
            port=self._runtime,
            payload=EmotionTextAgentInput(text=text, language=language, user_id=user_id),
            timeout_seconds=self._request_timeout_seconds,
        )

    async def infer_speech(
        self,
        *,
        audio_bytes: bytes,
        filename: str | None = None,
        content_type: str | None = None,
        transcription: str | None = None,
        language: str | None = None,
        user_id: str | None = None,
    ):
        if not self._inference_enabled:
            raise EmotionAgentDisabledError("emotion inference is disabled")
        if not self._speech_enabled:
            raise EmotionSpeechDisabledError("speech emotion inference is disabled")
        return await infer_speech_emotion(
            port=self._runtime,
            payload=EmotionSpeechAgentInput(
                audio_bytes=audio_bytes,
                filename=filename,
                content_type=content_type,
                transcription=transcription,
                language=language,
                user_id=user_id,
            ),
            timeout_seconds=self._request_timeout_seconds,
        )


    @property
    def inference_enabled(self) -> bool:
        return self._inference_enabled

    @property
    def speech_enabled(self) -> bool:
        return self._speech_enabled

    async def health(self) -> EmotionRuntimeHealth:
        health = await self._runtime.health()
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
