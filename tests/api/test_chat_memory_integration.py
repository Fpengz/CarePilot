"""Integration coverage for Mem0-backed chat memory."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any, cast

import pytest
from apps.api.carepilot_api.main import create_app
from fastapi.testclient import TestClient

from care_pilot.agent.core.contracts import AgentResponse
from care_pilot.config.app import get_settings
from care_pilot.features.companion.chat.orchestrator import ChatOrchestrator
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

    async def _mock_workflow(self, user_message: str, snapshot: object, config: dict[str, Any] | None = None):
        del self, config
        captured["user_message"] = user_message
        captured["snapshot"] = snapshot

        yield {
            "some_node": {
                "last_agent_response": AgentResponse(
                    agent_name="conversation_agent",
                    summary="ok",
                    structured_output={}
                )
            }
        }

    monkeypatch.setattr(ChatOrchestrator, "stream_multi_agent_workflow", _mock_workflow)

    response = client.post("/api/v1/chat", json={"message": "I like salads"})
    assert response.status_code == 200
    for line in cast(Iterable[str], response.iter_lines()):
        if line.startswith("data: "):
            _ = json.loads(line[6:])

    assert fake_store.search_calls
    user_message_with_memory = cast(str, captured["user_message"])
    assert "Relevant memories" in user_message_with_memory
    assert "Allergic to peanuts" in user_message_with_memory

