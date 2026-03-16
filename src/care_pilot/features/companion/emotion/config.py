"""
Define configuration for the emotion inference runtime.

This module provides configuration defaults and settings used to wire
emotion model loading and execution.
"""

from __future__ import annotations

from dataclasses import dataclass

from care_pilot.config.app import AppSettings as Settings


@dataclass(frozen=True, slots=True)
class EmotionRuntimeConfig:
    text_model_id: str
    speech_model_id: str
    fusion_model_id: str | None
    asr_model_id: str
    history_window: int
    model_device: str
    source_commit: str
    model_cache_dir: str | None

    @classmethod
    def from_settings(cls, settings: Settings) -> EmotionRuntimeConfig:
        return cls(
            text_model_id=settings.emotion.text_model_id,
            speech_model_id=settings.emotion.speech_model_id,
            fusion_model_id=settings.emotion.fusion_model_id,
            asr_model_id=settings.emotion.asr_model_id,
            history_window=settings.emotion.history_window,
            model_device=settings.emotion.model_device,
            source_commit=settings.emotion.source_commit,
            model_cache_dir=settings.emotion.model_cache_dir,
        )
