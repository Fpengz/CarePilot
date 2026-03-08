"""In-process emotion runtime extracted from ai_challenger-compatible contracts."""

from .ai_challenger_adapter import AI_CHALLENGER_SOURCE_COMMIT, to_compat_response
from .config import EmotionRuntimeConfig
from .inprocess_emotion_runtime import InProcessEmotionRuntime

__all__ = [
    "AI_CHALLENGER_SOURCE_COMMIT",
    "EmotionRuntimeConfig",
    "InProcessEmotionRuntime",
    "to_compat_response",
]

