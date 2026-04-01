"""
Provide in-memory coordination locks.

This module implements coordination primitives for local execution.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import Condition, Lock
from typing import Any


class InMemoryCoordinationStore:
    def __init__(self) -> None:
        self._signals: dict[str, list[dict[str, Any]]] = {}
        self._locks: dict[str, tuple[str, datetime]] = {}
        self._values: dict[str, tuple[str, datetime]] = {}
        self._lock = Lock()
        self._condition = Condition(self._lock)

    def set_value(self, key: str, value: str, *, ttl_seconds: int) -> None:
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        with self._lock:
            self._values[key] = (value, expires_at)

    def get_value(self, key: str) -> str | None:
        now = datetime.now(UTC)
        with self._lock:
            existing = self._values.get(key)
            if existing is None:
                return None
            value, expires_at = existing
            if now > expires_at:
                self._values.pop(key, None)
                return None
            return value

    def acquire_lock(self, key: str, *, owner: str, ttl_seconds: int) -> bool:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=ttl_seconds)
        with self._lock:
            existing = self._locks.get(key)
            if existing is not None:
                existing_owner, existing_expires = existing
                if now < existing_expires and existing_owner != owner:
                    return False
            self._locks[key] = (owner, expires_at)
            return True

    def release_lock(self, key: str, *, owner: str) -> bool:
        with self._lock:
            existing = self._locks.get(key)
            if existing is None:
                return False
            existing_owner, _ = existing
            if existing_owner != owner:
                return False
            self._locks.pop(key, None)
            return True

    def publish_signal(self, channel: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._signals.setdefault(channel, []).append(dict(payload))
            self._condition.notify_all()

    def drain_signals(self, channel: str) -> list[dict[str, Any]]:
        with self._lock:
            return self._signals.pop(channel, [])

    def wait_for_signal(self, channel: str, *, timeout_seconds: float) -> dict[str, Any] | None:
        with self._lock:
            items = self._signals.get(channel)
            if items:
                return items.pop(0)
            self._condition.wait(timeout_seconds)
            items = self._signals.get(channel)
            if not items:
                return None
            return items.pop(0)

    def close(self) -> None:
        return None
