from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any


class InMemoryCacheStore:
    def __init__(self) -> None:
        self._items: dict[str, tuple[datetime | None, Any]] = {}
        self._lock = Lock()

    def get_json(self, key: str) -> Any | None:
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at is not None and datetime.now(timezone.utc) >= expires_at:
                self._items.pop(key, None)
                return None
            return value

    def set_json(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            if ttl_seconds is not None
            else None
        )
        with self._lock:
            self._items[key] = (expires_at, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._items.pop(key, None)

    def close(self) -> None:
        return None
