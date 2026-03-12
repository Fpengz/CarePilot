"""
Provide an in-process emotion inference runtime.

This module executes emotion inference locally using the configured
emotion pipeline and model adapters.
"""

from __future__ import annotations

from dietary_guardian.agent.emotion.config import EmotionRuntimeConfig
from dietary_guardian.agent.emotion.pipeline import EmotionPipeline
import torch

from dietary_guardian.agent.emotion.adapters.asr_meralion import MeralionASR
from dietary_guardian.agent.emotion.adapters.fusion_hf import HFFusion
from dietary_guardian.agent.emotion.adapters.speech_hf import HFSpeechEmotion
from dietary_guardian.agent.emotion.adapters.text_hf import HFTextEmotion
from dietary_guardian.agent.emotion.audio_preprocessor import preprocess_audio
from dietary_guardian.features.companion.engagement.emotion.ports import (
    EmotionInferencePort,
    SpeechEmotionInput,
    TextEmotionInput,
)
from dietary_guardian.features.companion.core.health.emotion import (
    EmotionContextFeatures,
    EmotionInferenceResult,
    EmotionRuntimeHealth,
)


class InProcessEmotionRuntime(EmotionInferencePort):
    def __init__(self, config: EmotionRuntimeConfig, *, pipeline: EmotionPipeline | None = None) -> None:
        self._config = config
        device = _resolve_device(config.model_device)
        self._pipeline = pipeline or EmotionPipeline(
            asr=MeralionASR(config.asr_model_id),
            text=HFTextEmotion(config.text_model_id, device),
            speech=HFSpeechEmotion(config.speech_model_id, device),
            fusion=self._build_fusion(config, device=device),
        )

    def infer_text(self, payload: TextEmotionInput) -> EmotionInferenceResult:
        context = payload.context or _default_context()
        return self._pipeline.infer_text(
            text=payload.text,
            language=payload.language,
            context=context,
        )

    def infer_speech(self, payload: SpeechEmotionInput) -> EmotionInferenceResult:
        context = payload.context or _default_context()
        audio_bytes = preprocess_audio(payload.audio_bytes, content_type=payload.content_type)
        return self._pipeline.infer_speech(
            audio_bytes=audio_bytes,
            filename=payload.filename,
            language=payload.language,
            transcription=payload.transcription,
            context=context,
        )

    def health(self) -> EmotionRuntimeHealth:
        if not self._config.fusion_model_id:
            return EmotionRuntimeHealth(
                status="degraded",
                model_cache_ready=False,
                source_commit=self._config.source_commit,
                detail="fusion model not configured",
            )
        return EmotionRuntimeHealth(
            status="ready",
            model_cache_ready=True,
            source_commit=self._config.source_commit,
            detail=None,
        )

    @staticmethod
    def _build_fusion(config: EmotionRuntimeConfig, *, device: str) -> HFFusion:
        if not config.fusion_model_id:
            raise ValueError("fusion model not configured")
        return HFFusion(config.fusion_model_id, device)


def _default_context() -> EmotionContextFeatures:
    return EmotionContextFeatures(recent_labels=[], trend="stable")


def _resolve_device(model_device: str) -> str:
    if model_device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return model_device
