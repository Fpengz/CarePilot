"""In-process emotion runtime extracted from ai_challenger contracts."""

from .config import EmotionRuntimeConfig
from .inprocess_emotion_runtime import InProcessEmotionRuntime

__all__ = [
    "EmotionRuntimeConfig",
    "InProcessEmotionRuntime",
]
