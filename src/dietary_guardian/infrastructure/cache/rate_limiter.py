"""Infrastructure support for rate limiter."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import time
from typing import Protocol

from dietary_guardian.config.app import AppSettings as Settings

from .redis_store import _load_redis_module


class RateLimiter(Protocol):
    def allow(self, *, key: str, limit: int, window_seconds: int) -> tuple[bool, int]: ...


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, *, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time()
        cutoff = now - float(window_seconds)
        with self._lock:
            events = self._events.setdefault(key, deque())
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = int(max(1, window_seconds - (now - events[0]))) if events else window_seconds
                return (False, retry_after)
            events.append(now)
            return (True, 0)


@dataclass
class RedisRateLimiter:
    redis_url: str
    namespace: str

    def __post_init__(self) -> None:
        redis_module = _load_redis_module()
        self._client = redis_module.Redis.from_url(self.redis_url, decode_responses=True)

    def _key(self, key: str) -> str:
        return f"{self.namespace}:rate_limit:v2:{key}"

    def allow(self, *, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        namespaced_key = self._key(key)
        with self._client.pipeline() as pipe:
            pipe.incr(namespaced_key)
            pipe.ttl(namespaced_key)
            current_count, ttl_seconds = pipe.execute()
        count = int(current_count)
        ttl = int(ttl_seconds)
        if count == 1 or ttl < 0:
            self._client.expire(namespaced_key, int(window_seconds))
            ttl = int(window_seconds)
        if count > limit:
            return (False, max(1, ttl))
        return (True, 0)

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if callable(close):
            close()


def build_rate_limiter(settings: Settings) -> RateLimiter:
    if settings.storage.ephemeral_state_backend == "redis" and settings.storage.redis_url:
        return RedisRateLimiter(
            redis_url=str(settings.storage.redis_url),
            namespace=settings.storage.redis_namespace,
        )
    return InMemoryRateLimiter()
