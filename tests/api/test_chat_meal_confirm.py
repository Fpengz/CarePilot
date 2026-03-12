"""Tests for chat meal logging confirmation."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.dietary_api.main import create_app
from apps.api.dietary_api.services.chat_meal_intent import meal_proposal_cache_key
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


def test_confirm_meal_proposal_logs_meal() -> None:
    app = create_app()
    client = TestClient(app)
    _login(client)

    ctx = app.state.ctx
    sessions = ctx.auth_store.list_sessions_for_user("user_001")
    session_id = sessions[0]["session_id"]
    proposal_id = str(uuid4())
    cache_key = meal_proposal_cache_key(user_id="user_001", session_id=session_id, proposal_id=proposal_id)
    ctx.cache_store.set_json(
        cache_key,
        {
            "proposal_id": proposal_id,
            "user_id": "user_001",
            "session_id": session_id,
            "meal_text": "Chicken rice",
        },
        ttl_seconds=600,
    )

    before_count = len(ctx.stores.meals.list_validated_meal_events("user_001"))

    async def _fake_stream(self, *, messages, model_id=None):  # type: ignore[no-untyped-def]
        del self, messages, model_id
        yield "Follow-up guidance."

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(ChatStreamRuntime, "stream", _fake_stream)

    response = client.post(
        "/api/v1/chat/meal/confirm",
        json={"proposal_id": proposal_id, "action": "confirm"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "logged"
    assert "assistant_followup" in body
    assert "Follow-up guidance." in body["assistant_followup"]
    assert len(ctx.stores.meals.list_validated_meal_events("user_001")) == before_count + 1

    monkeypatch.undo()
