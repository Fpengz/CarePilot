from __future__ import annotations

from dietary_guardian.infrastructure.emotion.config import EmotionRuntimeConfig


class EmotionModelLoader:
    def __init__(self, config: EmotionRuntimeConfig) -> None:
        self._config = config
        self._loaded = False
        self._model_name = "ai_challenger_runtime"
        self._model_version = "heuristic-v1"

    def ensure_loaded(self) -> None:
        self._loaded = True

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def is_ready(self) -> bool:
        return self._loaded
