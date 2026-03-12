"""Tests for ChatAgent stream event envelopes."""

from __future__ import annotations

import asyncio

from dietary_guardian.agent.chat.agent import ChatAgent
from dietary_guardian.agent.chat.memory import MemoryManager
from dietary_guardian.agent.chat.schemas import ChatStreamEvent


class _DummyInferenceEngine:
    async def infer(self, request):  # pragma: no cover - should not be called in these tests.
        raise AssertionError("Inference should not run during stream event tests")


class _DummyStreamRuntime:
    async def stream(self, *, messages, model_id=None):
        yield "Hello"
        yield " world"


def test_stream_events_emits_token_and_done(tmp_path):
    async def _run():
        memory = MemoryManager(
            user_id="user-1",
            session_id="session-1",
            inference_engine=_DummyInferenceEngine(),
            db_path=tmp_path / "chat_memory.db",
        )
        agent = ChatAgent(stream_runtime=_DummyStreamRuntime(), router=None, memory=memory, model_id="test-model")

        events: list[ChatStreamEvent] = []
        async for event in agent.stream_events(user_message="Hi"):
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
        agent = ChatAgent(stream_runtime=_DummyStreamRuntime(), router=None, memory=memory, model_id="test-model")

        events: list[ChatStreamEvent] = []
        async for event in agent.stream_events(user_message="[TRACK] weight 70kg"):
            events.append(event)
        return events

    events = asyncio.run(_run())

    assert [event.event for event in events] == ["token", "done"]
    assert events[-1].data.get("status") == "tracked"
