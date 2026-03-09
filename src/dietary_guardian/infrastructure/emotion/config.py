from __future__ import annotations

from dataclasses import dataclass

from dietary_guardian.config.settings import Settings


@dataclass(frozen=True, slots=True)
class EmotionRuntimeConfig:
    text_model_id: str
    speech_model_id: str
    model_device: str
    source_commit: str

    @classmethod
    def from_settings(cls, settings: Settings) -> "EmotionRuntimeConfig":
        return cls(
            text_model_id=settings.emotion.text_model_id,
            speech_model_id=settings.emotion.speech_model_id,
            model_device=settings.emotion.model_device,
            source_commit=settings.emotion.source_commit,
        )

