from __future__ import annotations

import json
from typing import Any, cast


def _load_redis_module() -> Any:
    try:
        import redis
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "redis package is required for EPHEMERAL_STATE_BACKEND=redis. Run `uv sync` after updating dependencies."
        ) from exc
    return redis


class RedisCoordinationStore:
    def __init__(self, *, redis_url: str, namespace: str, keyspace_version: str = "v2") -> None:
        redis_module = _load_redis_module()
        self._client = redis_module.Redis.from_url(redis_url, decode_responses=True)
        self._namespace = namespace
        if keyspace_version != "v2":
            raise ValueError("Redis coordination store requires keyspace_version='v2'")
        self._release_script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        end
        return 0
        """

    def _domain(self, value: str) -> str:
        lowered = value.lower()
        if "reminder" in lowered:
            return "reminder"
        if "outbox" in lowered or "workflow" in lowered or "worker" in lowered:
            return "workflow"
        if "notification" in lowered:
            return "notification"
        return "coordination"

    def _key(self, key: str) -> str:
        return f"{self._namespace}:coordination:lock:{self._domain(key)}:{key}"

    def _channel(self, channel: str) -> str:
        return f"{self._namespace}:coordination:signal:{self._domain(channel)}:{channel}"

    def acquire_lock(self, key: str, *, owner: str, ttl_seconds: int) -> bool:
        return bool(self._client.set(self._key(key), owner, nx=True, ex=ttl_seconds))

    def release_lock(self, key: str, *, owner: str) -> bool:
        released = self._client.eval(self._release_script, 1, self._key(key), owner)
        return bool(released)

    def publish_signal(self, channel: str, payload: dict[str, Any]) -> None:
        self._client.lpush(self._channel(channel), json.dumps(payload))

    def drain_signals(self, channel: str) -> list[dict[str, Any]]:
        queue_key = self._channel(channel)
        items: list[dict[str, Any]] = []
        while True:
            payload = self._client.rpop(queue_key)
            if payload is None:
                break
            items.append(json.loads(payload))
        return items

    def wait_for_signal(self, channel: str, *, timeout_seconds: float) -> dict[str, Any] | None:
        result = self._client.brpop(self._channel(channel), timeout=max(1, int(timeout_seconds)))
        if result is None:
            return None
        _, payload = result
        return cast(dict[str, Any], json.loads(payload))

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if callable(close):
            close()
