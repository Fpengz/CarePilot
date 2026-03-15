"""
Provide SEA-LION chat runtime adapters for streaming and structured inference.

This module centralizes the SEA-LION OpenAI-compatible client wiring so chat
subsystems can reuse a consistent provider configuration, retry policy, and
timeout configuration.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, cast

from openai import AsyncOpenAI, BadRequestError
from openai.types.chat import ChatCompletionMessageParam
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from care_pilot.agent.runtime.inference_engine import InferenceEngine
from care_pilot.config.app import AppSettings
from care_pilot.config.llm import LLMCapability, ModelProvider
from care_pilot.platform.observability import get_logger

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

    @staticmethod
    def _is_non_retryable(exc: Exception) -> bool:
        if isinstance(exc, BadRequestError):
            message = str(exc).lower()
            if "roles must alternate" in message:
                return True
        return False

    def _requires_user_only_payload(self, model: str) -> bool:
        base_url = (self._config.base_url or "").lower()
        if "sea-lion.ai" in base_url:
            return True
        return "sea-lion" in model.lower()

    @staticmethod
    def _safe_preview(text: str, *, limit: int = 160) -> str:
        preview = text[:limit].replace("\n", " ")
        preview = re.sub(r"[0-9]", "x", preview)
        preview = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "[redacted-email]", preview)
        return preview

    def _normalize_messages_for_sealion(
        self,
        messages: list[ChatCompletionMessageParam],
    ) -> tuple[list[ChatCompletionMessageParam], bool, str | None]:
        normalized = [dict(message) for message in messages]
        system_chunks = [
            str(message.get("content"))
            for message in normalized
            if message.get("role") == "system" and message.get("content")
        ]
        if not system_chunks:
            return messages, False, None

        system_context = "\n\n".join(system_chunks)
        non_system = [message for message in normalized if message.get("role") != "system"]
        if not non_system:
            non_system = [
                {
                    "role": "user",
                    "content": f"[System context]\n{system_context}",
                }
            ]
        else:
            first = non_system[0]
            if first.get("role") != "user":
                non_system.insert(0, {"role": "user", "content": ""})
                first = non_system[0]
            existing = str(first.get("content") or "")
            prefix = f"[System context]\n{system_context}"
            first["content"] = f"{prefix}\n\n{existing}" if existing else prefix
        preview = self._safe_preview(system_context)
        return (
            cast(list[ChatCompletionMessageParam], non_system),
            True,
            preview,
        )

    def _log_request(self, *, model: str, messages: list[ChatCompletionMessageParam]) -> None:
        if not messages:
            return
        first = messages[0]
        content = str(first.get("content") or "")
        logger.info(
            "chat_api_request model=%s role=%s content_preview=%s",
            model,
            first.get("role"),
            self._safe_preview(content),
        )

    def _log_response(self, *, model: str, content: str) -> None:
        if not content:
            return
        logger.info(
            "chat_api_response model=%s content_len=%s preview=%s",
            model,
            len(content),
            self._safe_preview(content),
        )

    async def complete(self, *, messages: list[dict[str, Any]], model_id: str | None = None) -> str:
        model = model_id or self._config.model_id
        typed_messages = cast(list[ChatCompletionMessageParam], messages)
        if self._requires_user_only_payload(model):
            typed_messages, applied, preview = self._normalize_messages_for_sealion(typed_messages)
            if applied:
                logger.info(
                    "chat_payload_normalized applied=%s model=%s preview=%s",
                    applied,
                    model,
                    preview or "",
                )
        self._log_request(model=model, messages=typed_messages)
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=typed_messages,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("chat_complete_failed error=%s", exc)
            raise
        content = (response.choices[0].message.content or "").strip()
        self._log_response(model=model, content=content)
        return content

    async def stream(
        self, *, messages: list[dict[str, Any]], model_id: str | None = None
    ) -> AsyncIterator[str]:
        model = model_id or self._config.model_id
        attempts = self._config.stream_max_retries + 1
        typed_messages = cast(list[ChatCompletionMessageParam], messages)
        applied = False
        preview: str | None = None
        if self._requires_user_only_payload(model):
            typed_messages, applied, preview = self._normalize_messages_for_sealion(typed_messages)
            if applied:
                logger.info(
                    "chat_payload_normalized applied=%s model=%s preview=%s",
                    applied,
                    model,
                    preview or "",
                )
        self._log_request(model=model, messages=typed_messages)
        for attempt in range(1, attempts + 1):
            try:
                stream = await self._client.chat.completions.create(
                    model=model,
                    messages=typed_messages,
                    stream=True,
                )
                aggregated = ""
                async for chunk in stream:
                    token = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                    if token:
                        aggregated += token
                        yield token
                self._log_response(model=model, content=aggregated)
                return
            except Exception as exc:  # noqa: BLE001
                if attempt >= attempts:
                    logger.exception(
                        "chat_stream_failed attempt=%s/%s error=%s",
                        attempt,
                        attempts,
                        exc,
                    )
                    raise
                if self._is_non_retryable(exc):
                    logger.exception(
                        "chat_stream_non_retryable attempt=%s/%s error=%s normalized=%s",
                        attempt,
                        attempts,
                        exc,
                        applied,
                    )
                    raise
                logger.warning(
                    "chat_stream_retry attempt=%s/%s error=%s",
                    attempt,
                    attempts,
                    exc,
                )
                await asyncio.sleep(self._config.stream_backoff_seconds * attempt)
