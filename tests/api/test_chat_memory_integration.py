"""Integration coverage for Mem0-backed chat memory."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import cast

import pytest
from apps.api.carepilot_api.main import create_app
from fastapi.testclient import TestClient

from care_pilot.agent.runtime.chat_runtime import ChatStreamRuntime
from care_pilot.config.app import get_settings
from care_pilot.platform.memory import MemorySnippet, MemoryStore


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_STORE_BACKEND", "in_memory")
    monkeypatch.setenv("AUTH_SEED_DEMO_USERS", "true")
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "member@example.com", "password": "member-pass"},
    )
    assert response.status_code == 200


class _FakeMemoryStore(MemoryStore):
    def __init__(self) -> None:
        self.search_calls: list[dict] = []
        self.add_calls: list[dict] = []

    @property
    def enabled(self) -> bool:
        return True

    def search(self, *, user_id: str, query: str, limit: int) -> list[MemorySnippet]:
        self.search_calls.append({"user_id": user_id, "query": query, "limit": limit})
        return [MemorySnippet(text="Allergic to peanuts", score=0.82)]

    def add_messages(
        self,
        *,
        user_id: str,
        session_id: str,
        messages: list[dict[str, str]],
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.add_calls.append(
            {
                "user_id": user_id,
                "session_id": session_id,
                "messages": messages,
                "metadata": metadata or {},
            }
        )


def test_chat_uses_memory_and_records_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    client = TestClient(app)
    _login(client)

    fake_store = _FakeMemoryStore()
    app.state.ctx.memory_store = fake_store

    captured: dict[str, object] = {}

    async def _fake_stream(
        self,
        *,
        messages: list[dict[str, object]],
        model_id: str | None = None,
    ):
        del self, model_id
        captured["messages"] = messages
        yield "ok"

    monkeypatch.setattr(ChatStreamRuntime, "stream", _fake_stream)

    response = client.post("/api/v1/chat", json={"message": "I like salads"})
    assert response.status_code == 200
    for line in cast(Iterable[str], response.iter_lines()):
        if line.startswith("data: "):
            _ = json.loads(line[6:])

    assert fake_store.search_calls
    messages = cast(list[dict[str, object]], captured["messages"])
    user_message = [cast(str, m["content"]) for m in messages if m.get("role") == "user"][-1]
    assert "Relevant memories" in user_message
    assert "Allergic to peanuts" in user_message
    assert fake_store.add_calls
    assert fake_store.add_calls[0]["messages"][-1]["content"] == "ok"
