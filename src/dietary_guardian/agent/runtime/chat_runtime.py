"""
Provide SEA-LION chat runtime adapters for streaming and structured inference.

This module centralizes the SEA-LION OpenAI-compatible client wiring so chat
subsystems can reuse a consistent provider configuration, retry policy, and
timeout configuration.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from dietary_guardian.agent.runtime.inference_engine import InferenceEngine
from dietary_guardian.config.app import AppSettings
from dietary_guardian.config.llm import LLMCapability, ModelProvider
from dietary_guardian.platform.observability import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ChatRuntimeConfig:
    api_key: str
    base_url: str
    model_id: str
    reasoning_model_id: str
    timeout_seconds: float
    stream_max_retries: int
    stream_backoff_seconds: float


def build_chat_runtime_config(settings: AppSettings) -> ChatRuntimeConfig:
    chat_settings = settings.chat
    api_key = chat_settings.api_key or settings.llm.openai.api_key or ""
    timeout_seconds = float(settings.llm.openai.request_timeout_seconds)
    stream_max_retries = getattr(chat_settings, "stream_max_retries", 2)
    stream_backoff_seconds = getattr(chat_settings, "stream_backoff_seconds", 0.5)
    return ChatRuntimeConfig(
        api_key=api_key,
        base_url=str(chat_settings.base_url),
        model_id=chat_settings.model_id,
        reasoning_model_id=chat_settings.reasoning_model_id,
        timeout_seconds=timeout_seconds,
        stream_max_retries=int(stream_max_retries),
        stream_backoff_seconds=float(stream_backoff_seconds),
    )


def build_chat_inference_engine(
    settings: AppSettings,
    *,
    model_id: str,
    capability: LLMCapability | str = LLMCapability.CHATBOT,
) -> InferenceEngine:
    runtime_config = build_chat_runtime_config(settings)
    provider = OpenAIProvider(
        openai_client=AsyncOpenAI(
            api_key=runtime_config.api_key,
            base_url=runtime_config.base_url,
            timeout=runtime_config.timeout_seconds,
            max_retries=settings.llm.openai.transport_max_retries,
        )
    )
    model = OpenAIChatModel(model_id, provider=provider)
    return InferenceEngine(
        provider=ModelProvider.OPENAI.value,
        model_name=model_id,
        model=model,
        settings=settings,
        capability=capability,
    )


class ChatStreamRuntime:
    """Execute SEA-LION chat completions with retry and streaming support."""

    def __init__(self, settings: AppSettings) -> None:
        self._config = build_chat_runtime_config(settings)
        self._client = AsyncOpenAI(
            api_key=self._config.api_key,
            base_url=self._config.base_url,
            timeout=self._config.timeout_seconds,
            max_retries=settings.llm.openai.transport_max_retries,
        )

    async def complete(self, *, messages: list[dict[str, Any]], model_id: str | None = None) -> str:
        model = model_id or self._config.model_id
        typed_messages = cast(list[ChatCompletionMessageParam], messages)
        response = await self._client.chat.completions.create(
            model=model,
            messages=typed_messages,
        )
        return (response.choices[0].message.content or "").strip()

    async def stream(self, *, messages: list[dict[str, Any]], model_id: str | None = None) -> AsyncIterator[str]:
        model = model_id or self._config.model_id
        attempts = self._config.stream_max_retries + 1
        typed_messages = cast(list[ChatCompletionMessageParam], messages)
        for attempt in range(1, attempts + 1):
            try:
                stream = await self._client.chat.completions.create(
                    model=model,
                    messages=typed_messages,
                    stream=True,
                )
                async for chunk in stream:
                    token = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                    if token:
                        yield token
                return
            except Exception as exc:  # noqa: BLE001
                if attempt >= attempts:
                    logger.exception("chat_stream_failed attempt=%s/%s error=%s", attempt, attempts, exc)
                    raise
                logger.warning("chat_stream_retry attempt=%s/%s error=%s", attempt, attempts, exc)
                await asyncio.sleep(self._config.stream_backoff_seconds * attempt)
