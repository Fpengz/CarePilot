"""
Verify the emotion agent and its in-process/remote runtimes.
"""

from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest

from care_pilot.agent.emotion.agent import EmotionAgent
from care_pilot.agent.emotion.schemas import (
    EmotionContextFeatures,
    EmotionFusionOutput,
    EmotionInferenceResult,
    EmotionLabel,
    EmotionProductState,
    EmotionRuntimeHealth,
    EmotionSpeechAgentInput,
    EmotionTextAgentInput,
    FusionTrace,
    SpeechEmotionBranchResult,
    TextEmotionBranchResult,
)
from care_pilot.features.companion.emotion.config import EmotionRuntimeConfig
from care_pilot.features.companion.emotion.ports import EmotionInferencePort
from care_pilot.features.companion.emotion.runtime import InProcessEmotionRuntime


class _StubASR:
    def transcribe(self, audio_bytes: bytes, **kwargs: Any) -> str:
        del audio_bytes, kwargs
        return "transcription"


class _StubText:
    def predict(self, text: str, **kwargs: Any) -> TextEmotionBranchResult:
        del text, kwargs
        return TextEmotionBranchResult(
            transcript_or_text="I am happy and calm",
            emotion_scores={EmotionLabel.NEUTRAL: 0.9},
            predicted_emotion=EmotionLabel.NEUTRAL,
            confidence=0.9,
            model_name="stub-text",
        )


class _StubSpeech:
    def predict(self, audio_bytes: bytes, **kwargs: Any) -> SpeechEmotionBranchResult:
        del audio_bytes, kwargs
        return SpeechEmotionBranchResult(
            predicted_emotion=EmotionLabel.NEUTRAL,
            emotion_scores={EmotionLabel.NEUTRAL: 0.8},
            confidence=0.8,
            model_name="stub-speech",
        )


class _StubContext:
    def extract(self, user_id: str | None) -> EmotionContextFeatures:
        del user_id
        return EmotionContextFeatures(
            trend="stable",
        )


class _StubFusion:
    def predict(self, **kwargs: Any) -> tuple[EmotionFusionOutput, FusionTrace]:
        del kwargs
        return EmotionFusionOutput(
            emotion_label=EmotionLabel.NEUTRAL,
            product_state=EmotionProductState.STABLE,
            confidence=0.85,
        ), FusionTrace(
            fusion_inputs={},
            weighting_strategy="stub",
            final_decision_reason="stub reasoning",
        )


def _runtime() -> InProcessEmotionRuntime:
    from care_pilot.features.companion.emotion.pipeline import EmotionPipeline
    return InProcessEmotionRuntime(
        config=EmotionRuntimeConfig(
            asr_model_id="stub",
            text_model_id="stub",
            speech_model_id="stub",
            source_commit="sha",
            runtime_mode="in_process",
            remote_base_url="http://localhost",
            history_window=5,
            model_device="cpu",
            fusion_model_id=None,
            model_cache_dir=None,
        ),
        pipeline=EmotionPipeline(
            asr=cast(Any, _StubASR()),
            text=cast(Any, _StubText()),
            speech=cast(Any, _StubSpeech()),
            context=cast(Any, _StubContext()),
            fusion=cast(Any, _StubFusion()),
        ),
    )


@pytest.mark.asyncio
async def test_inprocess_emotion_runtime_text_inference() -> None:
    runtime = _runtime()
    result = await runtime.infer_text(EmotionTextAgentInput(text="I am happy and calm"))

    assert result.source_type == "text"
    assert result.final_emotion == EmotionLabel.NEUTRAL
    assert result.product_state == EmotionProductState.STABLE


@pytest.mark.asyncio
async def test_inprocess_emotion_runtime_speech_inference() -> None:
    runtime = _runtime()
    result = await runtime.infer_speech(
        EmotionSpeechAgentInput(audio_bytes=b"fake-wave-data", content_type="audio/wav")
    )

    assert result.source_type == "mixed"
    assert result.product_state == EmotionProductState.STABLE


@pytest.mark.asyncio
async def test_inprocess_runtime_health_reports_ready_when_configured() -> None:
    runtime = _runtime()
    health = await runtime.health()
    assert health.status == "ready"


class _SlowPort(EmotionInferencePort):
    @property
    def runtime_mode(self) -> str:
        return "slow"

    async def infer_text(self, payload: EmotionTextAgentInput) -> EmotionInferenceResult:
        del payload
        await asyncio.sleep(0.05)
        return await _runtime().infer_text(EmotionTextAgentInput(text="neutral"))

    async def infer_speech(self, payload: EmotionSpeechAgentInput) -> EmotionInferenceResult:
        del payload
        return await _runtime().infer_speech(
            EmotionSpeechAgentInput(audio_bytes=b"fake", content_type="audio/wav")
        )

    async def health(self) -> EmotionRuntimeHealth:
        return EmotionRuntimeHealth(status="ready", model_cache_ready=True, source_commit="sha")


@pytest.mark.asyncio
async def test_emotion_service_times_out_with_wall_clock_limit() -> None:
    service = EmotionAgent(
        runtime=_SlowPort(),
        inference_enabled=True,
        speech_enabled=True,
        request_timeout_seconds=0.01,
    )

    with pytest.raises(service.timeout_error_type):
        await service.infer_text(text="hello")
