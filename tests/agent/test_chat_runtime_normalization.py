"""Tests for SEA-LION chat payload normalization."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from openai.types.chat import ChatCompletionMessageParam

from care_pilot.agent.runtime.chat_runtime import ChatStreamRuntime
from care_pilot.config.app import AppSettings


class _FakeStream:
    def __init__(self, chunks: list[Any]) -> None:
        self._chunks = chunks
        self._idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._idx >= len(self._chunks):
            raise StopAsyncIteration
        chunk = self._chunks[self._idx]
        self._idx += 1
        return chunk


def _settings_for_sealion() -> AppSettings:
    return AppSettings.from_environment()


def test_normalize_flattens_system_into_user() -> None:
    settings = _settings_for_sealion()
    runtime = ChatStreamRuntime(settings)
    messages = cast(
        list[ChatCompletionMessageParam],
        [
            {"role": "system", "content": "Context A"},
            {"role": "system", "content": "Context B"},
            {"role": "user", "content": "Hello"},
        ],
    )

    normalized, applied, preview = runtime._normalize_messages_for_sealion(
        messages
    )

    assert applied is True
    assert preview is not None
    assert len(normalized) == 1
    assert normalized[0]["role"] == "user"
    content = str(normalized[0]["content"])
    assert "Context A" in content
    assert "Context B" in content
    assert "Hello" in content


def test_normalize_no_system_is_noop() -> None:
    settings = _settings_for_sealion()
    runtime = ChatStreamRuntime(settings)
    messages = cast(
        list[ChatCompletionMessageParam],
        [{"role": "user", "content": "Hello"}],
    )

    normalized, applied, preview = runtime._normalize_messages_for_sealion(
        messages
    )

    assert applied is False
    assert preview is None
    assert normalized == messages


@pytest.mark.asyncio
async def test_stream_sends_user_only_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SEALION_BASE_URL", "https://api.sea-lion.ai/v1")
    settings = _settings_for_sealion()
    runtime = ChatStreamRuntime(settings)

    captured: dict[str, Any] = {}

    async def _fake_create(
        *, model: str, messages: list[dict[str, object]], stream: bool = False
    ):
        captured["messages"] = messages
        chunk = SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))]
        )
        return _FakeStream([chunk])

    monkeypatch.setattr(
        runtime._client.chat.completions, "create", _fake_create
    )

    source_messages = [
        {"role": "system", "content": "Context"},
        {"role": "user", "content": "Hello"},
    ]

    tokens = []
    async for token in runtime.stream(messages=source_messages):
        tokens.append(token)

    assert tokens == ["ok"]
    sent_messages = captured["messages"]
    assert len(sent_messages) == 1
    assert sent_messages[0]["role"] == "user"
    assert "Context" in str(sent_messages[0]["content"])
    assert "Hello" in str(sent_messages[0]["content"])
