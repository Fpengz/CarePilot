"""
Provide an in-process emotion inference runtime.

This module executes emotion inference locally using the configured
emotion pipeline and model adapters.
"""

from __future__ import annotations

import asyncio
import functools
import os
from typing import cast

import torch

from care_pilot.agent.emotion.schemas import (
    EmotionInferenceResult,
    EmotionRuntimeHealth,
    EmotionSpeechAgentInput,
    EmotionTextAgentInput,
)
from care_pilot.features.companion.emotion.adapters.asr_whisper import WhisperASR
from care_pilot.features.companion.emotion.adapters.fusion_hf import HFFusion
from care_pilot.features.companion.emotion.adapters.speech_hf import HFSpeechEmotion
from care_pilot.features.companion.emotion.adapters.text_hf import HFTextEmotion
from care_pilot.features.companion.emotion.audio_preprocessor import preprocess_audio
from care_pilot.features.companion.emotion.config import EmotionRuntimeConfig
from care_pilot.features.companion.emotion.context.context_feature_extractor import (
    TimelineContextFeatureExtractor,
    TimelineServiceProtocol,
)
from care_pilot.features.companion.emotion.fusion.heuristic_fusion import HeuristicFusion
from care_pilot.features.companion.emotion.pipeline import EmotionPipeline
from care_pilot.features.companion.emotion.ports import EmotionInferencePort, FusionPort
from care_pilot.platform.runtime.executors import get_ml_executor


class InProcessEmotionRuntime(EmotionInferencePort):
    def __init__(
        self,
        config: EmotionRuntimeConfig,
        *,
        pipeline: EmotionPipeline | None = None,
        event_timeline: object | None = None,
    ) -> None:
        self._config = config
        if config.model_cache_dir:
            os.environ.setdefault("HF_HOME", config.model_cache_dir)
            os.environ.setdefault("TRANSFORMERS_CACHE", config.model_cache_dir)
        device = _resolve_device(config.model_device)
        self._pipeline = pipeline or EmotionPipeline(
            asr=WhisperASR(config.asr_model_id, device, cache_dir=config.model_cache_dir),
            text=HFTextEmotion(config.text_model_id, device, cache_dir=config.model_cache_dir),
            speech=HFSpeechEmotion(
                config.speech_model_id, device, cache_dir=config.model_cache_dir
            ),
            context=TimelineContextFeatureExtractor(
                cast(TimelineServiceProtocol, event_timeline),
                history_window=config.history_window,
            ),
            fusion=self._build_fusion(config, device=device),
        )

    @property
    def runtime_mode(self) -> str:
        return "local"

    async def infer_text(self, payload: EmotionTextAgentInput) -> EmotionInferenceResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            get_ml_executor(),
            functools.partial(
                self._pipeline.infer_text,
                text=payload.text,
                language=payload.language,
                user_id=payload.user_id,
            ),
        )

    async def infer_speech(self, payload: EmotionSpeechAgentInput) -> EmotionInferenceResult:
        audio_bytes = preprocess_audio(payload.audio_bytes, content_type=payload.content_type)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            get_ml_executor(),
            functools.partial(
                self._pipeline.infer_speech,
                audio_bytes=audio_bytes,
                filename=payload.filename,
                language=payload.language,
                transcription=payload.transcription,
                user_id=payload.user_id,
            ),
        )

    async def health(self) -> EmotionRuntimeHealth:
        return EmotionRuntimeHealth(
            status="ready",
            model_cache_ready=True,
            source_commit=self._config.source_commit,
            detail=None,
        )

    @staticmethod
    def _build_fusion(config: EmotionRuntimeConfig, *, device: str) -> FusionPort:
        if not config.fusion_model_id:
            return HeuristicFusion()
        try:
            return HFFusion(config.fusion_model_id, device, cache_dir=config.model_cache_dir)
        except Exception:
            return HeuristicFusion()


def _resolve_device(model_device: str) -> str:
    if model_device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return model_device
