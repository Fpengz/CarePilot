"""Tests for coordination store."""

from threading import Thread
from time import sleep

from dietary_guardian.infrastructure.coordination.in_memory import InMemoryCoordinationStore


def test_in_memory_coordination_store_publish_and_drain_signal() -> None:
    store = InMemoryCoordinationStore()

    store.publish_signal("reminders.ready", {"user_id": "user_001"})

    items = store.drain_signals("reminders.ready")
    assert items == [{"user_id": "user_001"}]
    assert store.drain_signals("reminders.ready") == []


def test_in_memory_coordination_store_lock_is_exclusive() -> None:
    store = InMemoryCoordinationStore()

    first = store.acquire_lock("scheduler", owner="worker-a", ttl_seconds=30)
    second = store.acquire_lock("scheduler", owner="worker-b", ttl_seconds=30)
    released = store.release_lock("scheduler", owner="worker-a")
    third = store.acquire_lock("scheduler", owner="worker-b", ttl_seconds=30)

    assert first is True
    assert second is False
    assert released is True
    assert third is True


def test_in_memory_coordination_store_wait_for_signal_returns_published_payload() -> None:
    store = InMemoryCoordinationStore()

    def publish_later() -> None:
        sleep(0.05)
        store.publish_signal("workers.ready", {"kind": "reminders"})

    publisher = Thread(target=publish_later)
    publisher.start()
    try:
        payload = store.wait_for_signal("workers.ready", timeout_seconds=0.5)
    finally:
        publisher.join()

    assert payload == {"kind": "reminders"}


def test_in_memory_coordination_store_wait_for_signal_times_out_cleanly() -> None:
    store = InMemoryCoordinationStore()

    payload = store.wait_for_signal("workers.ready", timeout_seconds=0.01)

    assert payload is None
