from __future__ import annotations

import json
from typing import Any


def _load_redis_module() -> Any:
    try:
        import redis
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "redis package is required for EPHEMERAL_STATE_BACKEND=redis. Run `uv sync` after updating dependencies."
        ) from exc
    return redis


class RedisCacheStore:
    def __init__(self, *, redis_url: str, namespace: str) -> None:
        redis_module = _load_redis_module()
        self._client = redis_module.Redis.from_url(redis_url, decode_responses=True)
        self._namespace = namespace

    def _domain(self, key: str) -> str:
        key_lower = key.lower()
        if "reminder" in key_lower:
            return "reminder"
        if "notification" in key_lower:
            return "notification"
        if "workflow" in key_lower or "outbox" in key_lower:
            return "workflow"
        return "general"

    def _key(self, key: str) -> str:
        return f"{self._namespace}:cache:{self._domain(key)}:{key}"

    def get_json(self, key: str) -> Any | None:
        payload = self._client.get(self._key(key))
        return None if payload is None else json.loads(payload)

    def set_json(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        payload = json.dumps(value)
        if ttl_seconds is None:
            self._client.set(self._key(key), payload)
        else:
            self._client.setex(self._key(key), ttl_seconds, payload)

    def delete(self, key: str) -> None:
        self._client.delete(self._key(key))

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if callable(close):
            close()
