"""Emotion domain package — emotion inference models and agent schemas."""

# ruff: noqa: F401
from dietary_guardian.domain.emotion.schemas import (
    EmotionAgentOutput,
    EmotionSpeechAgentInput,
    EmotionTextAgentInput,
)

__all__ = [
    "EmotionAgentOutput",
    "EmotionSpeechAgentInput",
    "EmotionTextAgentInput",
]
