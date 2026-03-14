"""Tests for emotion service."""

from __future__ import annotations

import time

import pytest

from dietary_guardian.features.companion.emotion.ports import (
    EmotionInferencePort,
)
from dietary_guardian.features.companion.emotion.config import EmotionRuntimeConfig
from dietary_guardian.features.companion.emotion.pipeline import EmotionPipeline
from dietary_guardian.features.companion.emotion.runtime import InProcessEmotionRuntime
from dietary_guardian.agent.emotion.schemas import (
    EmotionContextFeatures,
    EmotionInferenceResult,
    EmotionLabel,
    EmotionProductState,
    EmotionSpeechAgentInput,
    EmotionTextAgentInput,
    EmotionRuntimeHealth,
)
from dietary_guardian.agent.emotion import EmotionAgent


class _StubASR:
    def transcribe(self, audio_bytes: bytes, *, filename: str | None, language: str | None) -> str:
        del audio_bytes, filename, language
        return "hello"


class _StubText:
    def predict(self, text: str, language: str | None) -> tuple[dict[EmotionLabel, float], str, str]:
        del text, language
        return {EmotionLabel.NEUTRAL: 0.7}, "text-model", "1"


class _StubSpeech:
    def predict(
        self, audio_bytes: bytes, *, transcript: str | None
    ) -> tuple[dict[EmotionLabel, float], dict[str, float], str, str]:
        del audio_bytes, transcript
        return {EmotionLabel.NEUTRAL: 0.6}, {"duration_sec": 1.2}, "speech-model", "1"


class _StubFusion:
    def predict(
        self,
        *,
        text_scores: dict[EmotionLabel, float],
        speech_scores: dict[EmotionLabel, float] | None,
        context: EmotionContextFeatures,
    ) -> tuple[EmotionLabel, EmotionProductState, float, dict[EmotionLabel, float]]:
        del text_scores, speech_scores, context
        return EmotionLabel.NEUTRAL, EmotionProductState.STABLE, 0.72, {EmotionLabel.NEUTRAL: 0.72}


def _runtime() -> InProcessEmotionRuntime:
    return InProcessEmotionRuntime(
        EmotionRuntimeConfig(
            text_model_id="text-model",
            speech_model_id="speech-model",
            fusion_model_id="fusion-model",
            asr_model_id="MERaLiON/MERaLiON-2-3B",
            history_window=5,
            model_device="cpu",
            source_commit="9afc3f1a3a3fec71a4e5920d8f4103710b337ecc",
        ),
        pipeline=EmotionPipeline(
            asr=_StubASR(),
            text=_StubText(),
            speech=_StubSpeech(),
            fusion=_StubFusion(),
        ),
    )


def test_inprocess_emotion_runtime_text_inference() -> None:
    runtime = _runtime()
    result = runtime.infer_text(EmotionTextAgentInput(text="I am happy and calm"))

    assert result.source_type == "text"
    assert result.fusion.emotion_label == "neutral"
    assert result.fusion.product_state == "stable"


def test_inprocess_emotion_runtime_speech_inference() -> None:
    runtime = _runtime()
    result = runtime.infer_speech(
        EmotionSpeechAgentInput(audio_bytes=b"fake-wave-data", content_type="audio/wav")
    )

    assert result.source_type == "mixed"
    assert result.fusion.product_state == "stable"


def test_inprocess_runtime_health_reports_ready_when_configured() -> None:
    runtime = _runtime()
    health = runtime.health()
    assert health.status == "ready"

class _SlowPort(EmotionInferencePort):
    def infer_text(self, payload: EmotionTextAgentInput) -> EmotionInferenceResult:
        del payload
        time.sleep(0.05)
        return _runtime().infer_text(EmotionTextAgentInput(text="neutral"))

    def infer_speech(self, payload: EmotionSpeechAgentInput) -> EmotionInferenceResult:
        del payload
        return _runtime().infer_speech(
            EmotionSpeechAgentInput(audio_bytes=b"fake", content_type="audio/wav")
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
