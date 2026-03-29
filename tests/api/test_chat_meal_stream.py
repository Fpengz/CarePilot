"""Tests for meal logging chat stream continuation."""

from __future__ import annotations

import json
from typing import Any, TypedDict, cast

import pytest
from apps.api.carepilot_api.main import create_app
from fastapi.testclient import TestClient

from care_pilot.agent.chat.schemas import ChatStreamEvent
from care_pilot.agent.core.contracts import AgentResponse
from care_pilot.config.app import get_settings
from care_pilot.features.companion.chat.orchestrator import ChatOrchestrator


class _StreamEvent(TypedDict):
    event: str
    data: dict[str, object]


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


def test_meal_command_stream_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    client = TestClient(app)
    _login(client)

    async def _mock_workflow(*args, **kwargs):
        yield {
            "some_node": {
                "last_agent_response": AgentResponse(
                    agent_name="conversation_agent",
                    summary="Next guidance.",
                    structured_output={}
                )
            }
        }

    monkeypatch.setattr(ChatOrchestrator, "stream_multi_agent_workflow", _mock_workflow)

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


def test_chat_stream_continues_when_text_emotion_inference_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EMOTION_INFERENCE_ENABLED", "true")
    monkeypatch.setenv("EMOTION_RUNTIME_MODE", "remote")
    _reset_settings_cache()

    app = create_app()
    client = TestClient(app)
    _login(client)

    app.state.ctx.emotion_agent._inference_enabled = True

    async def _raise_emotion_failure(*, text: str, language: str | None = None, context: Any = None):
        del text, language, context
        raise RuntimeError("broken fusion model")

    async def _mock_workflow(*args, **kwargs):
        yield {
            "some_node": {
                "last_agent_response": AgentResponse(
                    agent_name="conversation_agent",
                    summary="Hello back.",
                    structured_output={}
                )
            }
        }

    monkeypatch.setattr(app.state.ctx.emotion_agent, "infer_text", _raise_emotion_failure)
    monkeypatch.setattr(ChatOrchestrator, "stream_multi_agent_workflow", _mock_workflow)


    response = client.post("/api/v1/chat", json={"message": "Hi"})
    assert response.status_code == 200

    events: list[_StreamEvent] = []
    for line in response.iter_lines():
        if not line.startswith("data: "):
            continue
        events.append(cast(_StreamEvent, json.loads(line[6:])))

    assert [event["event"] for event in events] == ["token", "done"]
    assert cast(str, events[0]["data"]["text"]) == "Hello back.\n\n"
    assert all(event["event"] != "error" for event in events)


def test_chat_audio_continues_when_speech_emotion_inference_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EMOTION_INFERENCE_ENABLED", "true")
    monkeypatch.setenv("EMOTION_SPEECH_ENABLED", "true")
    monkeypatch.setenv("EMOTION_RUNTIME_MODE", "remote")
    _reset_settings_cache()

    app = create_app()
    client = TestClient(app)
    _login(client)

    app.state.ctx.emotion_agent._inference_enabled = True
    app.state.ctx.emotion_agent._speech_enabled = True

    async def _fake_transcribe_bytes(raw_bytes: bytes, filename: str) -> str:
        del raw_bytes, filename
        return "Hello from audio"

    async def _raise_speech_emotion_failure(
        *,
        audio_bytes: bytes,
        filename: str | None = None,
        content_type: str | None = None,
        transcription: str | None = None,
        language: str | None = None,
        context: Any = None,
    ):
        del (
            audio_bytes,
            filename,
            content_type,
            transcription,
            language,
            context,
        )
        raise RuntimeError("broken fusion model")

    async def _fake_stream_events(
        self,
        *,
        user_message: str,
        request: Any,
        session: dict[str, object],
        ctx: Any,
        inputs: Any,
    ):
        del self, user_message, request, session, ctx, inputs
        yield ChatStreamEvent(event="token", data={"text": "Audio reply."})
        yield ChatStreamEvent(event="done", data={"status": "complete"})


    monkeypatch.setattr(
        app.state.ctx.chat_audio_agent,
        "transcribe_bytes",
        _fake_transcribe_bytes,
    )
    monkeypatch.setattr(
        app.state.ctx.emotion_agent,
        "infer_speech",
        _raise_speech_emotion_failure,
    )
    monkeypatch.setattr(ChatOrchestrator, "stream_events", _fake_stream_events)

    response = client.post(
        "/api/v1/chat/audio",
        files={"audio": ("sample.webm", b"fake-audio", "audio/webm")},
    )
    assert response.status_code == 200

    events: list[_StreamEvent] = []
    for line in response.iter_lines():
        if not line.startswith("data: "):
            continue
        events.append(cast(_StreamEvent, json.loads(line[6:])))

    assert [event["event"] for event in events] == [
        "transcribed",
        "token",
        "done",
    ]
    assert cast(str, events[0]["data"]["text"]) == "Hello from audio"
    assert cast(str, events[1]["data"]["text"]) == "Audio reply."
    assert all(event["event"] != "error" for event in events)
