"""Tests for meal logging chat stream continuation."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from apps.api.dietary_api.main import create_app
from dietary_guardian.agent.runtime.chat_runtime import ChatStreamRuntime
from dietary_guardian.config.app import get_settings


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


def test_meal_command_stream_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    client = TestClient(app)
    _login(client)

    async def _fake_stream(
        self,
        *,
        messages: list[dict[str, object]],
        model_id: str | None = None,
    ):
        del self, messages, model_id
        yield "Next guidance."

    monkeypatch.setattr(ChatStreamRuntime, "stream", _fake_stream)

    response = client.post("/api/v1/chat", json={"message": "[meal] Nasi Goreng"})
    assert response.status_code == 200

    tokens: list[str] = []
    for line in response.iter_lines():
        if not line.startswith("data: "):
            continue
        payload = json.loads(line[6:])
        if payload["event"] == "token":
            tokens.append(payload["data"]["text"])

    combined = "".join(tokens)
    assert "Logged meal: Nasi Goreng." in combined
    assert "Next guidance." in combined
