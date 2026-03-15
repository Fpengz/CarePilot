"""Ensure chat memory and health tracking are scoped by user."""

from __future__ import annotations

from care_pilot.features.companion.chat.health_tracker import HealthTracker
from care_pilot.features.companion.chat.memory import MemoryManager


class _DummyInferenceEngine:
    async def infer(self, request):  # pragma: no cover - should not be called in these tests.
        raise AssertionError("Inference should not run during scoping tests")


def test_memory_scoped_by_user_and_session(tmp_path):
    db_path = tmp_path / "chat_memory.db"
    engine = _DummyInferenceEngine()

    memory_a = MemoryManager(
        user_id="user-a",
        session_id="session-1",
        inference_engine=engine,
        db_path=db_path,
    )
    memory_b = MemoryManager(
        user_id="user-b",
        session_id="session-1",
        inference_engine=engine,
        db_path=db_path,
    )

    memory_a.add_message("user", "hello from a")
    memory_b.add_message("user", "hello from b")

    assert memory_a.all_messages() == [{"role": "user", "content": "hello from a"}]
    assert memory_b.all_messages() == [{"role": "user", "content": "hello from b"}]


def test_health_tracker_filters_by_user(tmp_path):
    db_path = tmp_path / "chat_memory.db"
    engine = _DummyInferenceEngine()

    memory_a = MemoryManager(
        user_id="user-a",
        session_id="session-1",
        inference_engine=engine,
        db_path=db_path,
    )
    memory_b = MemoryManager(
        user_id="user-b",
        session_id="session-1",
        inference_engine=engine,
        db_path=db_path,
    )

    memory_a.add_message("user", "[TRACK] weight 80 kg")
    memory_b.add_message("user", "[TRACK] weight 70 kg")

    tracker_a = HealthTracker(
        user_id="user-a",
        session_id="session-1",
        inference_engine=engine,
        db_path=db_path,
    )
    tracker_b = HealthTracker(
        user_id="user-b",
        session_id="session-1",
        inference_engine=engine,
        db_path=db_path,
    )

    entries_a = tracker_a.get_raw_entries("2000-01-01", "2100-01-01")
    entries_b = tracker_b.get_raw_entries("2000-01-01", "2100-01-01")

    assert [row["content"] for row in entries_a] == ["[TRACK] weight 80 kg"]
    assert [row["content"] for row in entries_b] == ["[TRACK] weight 70 kg"]
