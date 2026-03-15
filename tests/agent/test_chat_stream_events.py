"""Tests for ChatOrchestrator stream event envelopes."""

from __future__ import annotations

import asyncio

from care_pilot.features.companion.chat.orchestrator import ChatOrchestrator
from care_pilot.features.companion.chat.memory import MemoryManager
from care_pilot.agent.chat.schemas import ChatStreamEvent


class _DummyInferenceEngine:
    async def infer(
        self, request
    ):  # pragma: no cover - should not be called in these tests.
        raise AssertionError(
            "Inference should not run during stream event tests"
        )


def test_stream_events_emits_token_and_done(tmp_path, monkeypatch):
    async def _run():
        memory = MemoryManager(
            user_id="user-1",
            session_id="session-1",
            inference_engine=_DummyInferenceEngine(),
            db_path=tmp_path / "chat_memory.db",
        )
        orchestrator = ChatOrchestrator(
            router=None,
            memory=memory,
        )

        async def mock_run_chat(*args, **kwargs):
            return "Hello world"

        monkeypatch.setattr(
            "care_pilot.features.companion.chat.orchestrator.run_chat",
            mock_run_chat,
        )

        events: list[ChatStreamEvent] = []
        async for event in orchestrator.stream_events(user_message="Hi"):
            events.append(event)
        return events

    events = asyncio.run(_run())

    assert events
    assert events[0].event == "token"
    assert events[-1].event == "done"


def test_stream_events_handles_track_shortcut(tmp_path):
    async def _run():
        memory = MemoryManager(
            user_id="user-1",
            session_id="session-1",
            inference_engine=_DummyInferenceEngine(),
            db_path=tmp_path / "chat_memory.db",
        )
        orchestrator = ChatOrchestrator(
            router=None,
            memory=memory,
        )

        events: list[ChatStreamEvent] = []
        async for event in orchestrator.stream_events(
            user_message="[TRACK] weight 70kg"
        ):
            events.append(event)
        return events

    events = asyncio.run(_run())

    assert [event.event for event in events] == ["token", "done"]
    assert events[-1].data.get("status") == "tracked"
