"""
Provide a remote emotion inference runtime.

This module executes emotion inference by calling an external inference service.
"""

from __future__ import annotations

from typing import cast

import httpx

from care_pilot.agent.emotion.schemas import (
    EmotionInferenceResult,
    EmotionRuntimeHealth,
    EmotionSpeechAgentInput,
    EmotionTextAgentInput,
)
from care_pilot.features.companion.emotion.config import EmotionRuntimeConfig
from care_pilot.features.companion.emotion.context.context_feature_extractor import (
    TimelineContextFeatureExtractor,
    TimelineServiceProtocol,
)
from care_pilot.features.companion.emotion.ports import EmotionInferencePort


class RemoteEmotionRuntime(EmotionInferencePort):
    def __init__(
        self,
        config: EmotionRuntimeConfig,
        *,
        event_timeline: object | None = None,
    ) -> None:
        self._config = config
        self._client = httpx.AsyncClient(base_url=config.remote_base_url, timeout=60.0)
        self._context_extractor = TimelineContextFeatureExtractor(
            cast(TimelineServiceProtocol, event_timeline),
            history_window=config.history_window,
        )

    @property
    def runtime_mode(self) -> str:
        return "remote"

    async def infer_text(self, payload: EmotionTextAgentInput) -> EmotionInferenceResult:
        context_features = self._context_extractor.extract(payload.user_id)
        data = {
            "text": payload.text,
            "language": payload.language,
            "user_id": payload.user_id,
            "context_features": context_features.model_dump(),
        }
        response = await self._client.post("/infer/text", json=data)
        response.raise_for_status()
        return EmotionInferenceResult.model_validate(response.json())

    async def infer_speech(self, payload: EmotionSpeechAgentInput) -> EmotionInferenceResult:
        context_features = self._context_extractor.extract(payload.user_id)
        files = {
            "audio": (payload.filename or "audio.wav", payload.audio_bytes, payload.content_type)
        }
        data = {
            "user_id": payload.user_id,
            "language": payload.language,
            "transcription": payload.transcription,
            "context_features": context_features.model_dump_json(),
        }
        response = await self._client.post("/infer/speech", data=data, files=files)
        response.raise_for_status()
        return EmotionInferenceResult.model_validate(response.json())

    async def health(self) -> EmotionRuntimeHealth:
        try:
            response = await self._client.get("/health")
            response.raise_for_status()
            return EmotionRuntimeHealth.model_validate(response.json())
        except Exception as exc:
            return EmotionRuntimeHealth(
                status="degraded",
                model_cache_ready=False,
                source_commit=self._config.source_commit,
                detail=str(exc),
            )

    async def close(self) -> None:
        await self._client.aclose()
