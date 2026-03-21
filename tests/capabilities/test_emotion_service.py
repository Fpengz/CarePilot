"""Tests for emotion service."""

from __future__ import annotations

import time

import pytest

from care_pilot.agent.emotion import EmotionAgent
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
from care_pilot.features.companion.emotion.pipeline import EmotionPipeline
from care_pilot.features.companion.emotion.ports import (
    EmotionInferencePort,
)
from care_pilot.features.companion.emotion.runtime import (
    InProcessEmotionRuntime,
)


class _StubASR:
    def transcribe(self, audio_bytes: bytes, *, filename: str | None, language: str | None) -> str:
        del audio_bytes, filename, language
        return "hello"


class _StubText:
    def predict(self, text: str, language: str | None) -> TextEmotionBranchResult:
        del language
        return TextEmotionBranchResult(
            transcript_or_text=text,
            emotion_scores={EmotionLabel.NEUTRAL: 0.7},
            predicted_emotion=EmotionLabel.NEUTRAL,
            confidence=0.7,
            model_name="text-model",
            metadata={},
        )


class _StubSpeech:
    def predict(self, audio_bytes: bytes, *, transcript: str | None) -> SpeechEmotionBranchResult:
        del audio_bytes
        return SpeechEmotionBranchResult(
            transcription=transcript,
            acoustic_scores={"duration_sec": 1.2},
            predicted_emotion=EmotionLabel.NEUTRAL,
            emotion_scores={EmotionLabel.NEUTRAL: 0.6},
            confidence=0.6,
            model_name="speech-model",
            metadata={},
        )


class _StubContext:
    def extract(self, user_id: str | None) -> EmotionContextFeatures:
        del user_id
        return EmotionContextFeatures(recent_labels=[], trend="stable", recent_product_states=[])


class _StubFusion:
    def predict(
        self,
        *,
        text_branch: TextEmotionBranchResult | None,
        speech_branch: SpeechEmotionBranchResult | None,
        context: EmotionContextFeatures,
    ) -> tuple[EmotionFusionOutput, FusionTrace]:
        del text_branch, speech_branch, context
        return EmotionFusionOutput(
            emotion_label=EmotionLabel.NEUTRAL,
            product_state=EmotionProductState.STABLE,
            confidence=0.72,
            logits={EmotionLabel.NEUTRAL: 0.72},
        ), FusionTrace(
            fusion_inputs={},
            weighting_strategy="stub",
            final_decision_reason="stub",
        )


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
            model_cache_dir=None,
            runtime_mode="in_process",
            remote_base_url="http://localhost:8002",
        ),
        pipeline=EmotionPipeline(
            asr=_StubASR(),
            text=_StubText(),
            speech=_StubSpeech(),
            context=_StubContext(),
            fusion=_StubFusion(),
        ),
    )


def test_inprocess_emotion_runtime_text_inference() -> None:
    runtime = _runtime()
    result = runtime.infer_text(EmotionTextAgentInput(text="I am happy and calm"))

    assert result.source_type == "text"
    assert result.final_emotion == "neutral"
    assert result.product_state == "stable"


def test_inprocess_emotion_runtime_speech_inference() -> None:
    runtime = _runtime()
    result = runtime.infer_speech(
        EmotionSpeechAgentInput(audio_bytes=b"fake-wave-data", content_type="audio/wav")
    )

    assert result.source_type == "mixed"
    assert result.product_state == "stable"


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
