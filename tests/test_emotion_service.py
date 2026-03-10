"""Tests for emotion service."""

from __future__ import annotations

import time

import pytest

from dietary_guardian.application.emotion.ports import (
    EmotionInferencePort,
    SpeechEmotionInput,
    TextEmotionInput,
)
from dietary_guardian.infrastructure.emotion import EmotionRuntimeConfig, InProcessEmotionRuntime
from dietary_guardian.models.emotion import EmotionInferenceResult, EmotionRuntimeHealth
from dietary_guardian.agents.emotion import EmotionAgent


def _runtime() -> InProcessEmotionRuntime:
    return InProcessEmotionRuntime(
        EmotionRuntimeConfig(
            text_model_id="text-model",
            speech_model_id="speech-model",
            model_device="cpu",
            source_commit="9afc3f1a3a3fec71a4e5920d8f4103710b337ecc",
        )
    )


def test_inprocess_emotion_runtime_text_inference() -> None:
    runtime = _runtime()
    result = runtime.infer_text(TextEmotionInput(text="I am happy and calm"))

    assert result.source_type == "text"
    assert result.emotion in {"happy", "neutral"}
    assert len(result.evidence) >= 1


def test_inprocess_emotion_runtime_speech_inference() -> None:
    runtime = _runtime()
    result = runtime.infer_speech(
        SpeechEmotionInput(audio_bytes=b"fake-wave-data", content_type="audio/wav")
    )

    assert result.source_type == "speech"
    assert len(result.evidence) >= 1


def test_inprocess_runtime_health_transitions_after_inference() -> None:
    runtime = _runtime()

    before = runtime.health()
    runtime.infer_text(TextEmotionInput(text="neutral"))
    after = runtime.health()

    assert before.status == "degraded"
    assert after.status == "ready"

class _SlowPort(EmotionInferencePort):
    def infer_text(self, payload: TextEmotionInput) -> EmotionInferenceResult:
        del payload
        time.sleep(0.05)
        return _runtime().infer_text(TextEmotionInput(text="neutral"))

    def infer_speech(self, payload: SpeechEmotionInput) -> EmotionInferenceResult:
        del payload
        return _runtime().infer_speech(
            SpeechEmotionInput(audio_bytes=b"fake", content_type="audio/wav")
        )

    def health(self) -> EmotionRuntimeHealth:
        return EmotionRuntimeHealth(status="ready", model_cache_ready=True, source_commit="sha")


def test_emotion_service_times_out_with_wall_clock_limit() -> None:
    service = EmotionAgent(
        runtime=_SlowPort(),
        inference_enabled=True,
        speech_enabled=True,
        request_timeout_seconds=0.001,
    )

    with pytest.raises(service.timeout_error_type):
        service.infer_text(text="hello")
