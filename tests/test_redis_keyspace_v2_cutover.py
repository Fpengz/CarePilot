from __future__ import annotations

import json

import pytest

from dietary_guardian.infrastructure.cache import redis_store as redis_cache_module
from dietary_guardian.infrastructure.coordination import redis_coordination as redis_coord_module


class _FakeRedisClient:
    def __init__(self) -> None:
        self.get_calls: list[str] = []
        self.rpop_calls: list[str] = []
        self.brpop_calls: list[tuple[str, int]] = []
        self._kv: dict[str, str] = {}
        self._lists: dict[str, list[str]] = {}
        self._brpop_result: tuple[str, str] | None = None

    def get(self, key: str) -> str | None:
        self.get_calls.append(key)
        return self._kv.get(key)

    def rpop(self, key: str) -> str | None:
        self.rpop_calls.append(key)
        values = self._lists.get(key, [])
        if not values:
            return None
        return values.pop()

    def brpop(self, key: str, *, timeout: int) -> tuple[str, str] | None:
        self.brpop_calls.append((key, timeout))
        return self._brpop_result

    def lpush(self, key: str, payload: str) -> None:
        self._lists.setdefault(key, []).insert(0, payload)

    def set(self, key: str, value: str, *, nx: bool, ex: int) -> bool:
        if nx and key in self._kv:
            return False
        self._kv[key] = value
        return True

    def eval(self, _script: str, _numkeys: int, key: str, owner: str) -> int:
        if self._kv.get(key) == owner:
            del self._kv[key]
            return 1
        return 0


class _FakeRedisModule:
    def __init__(self, client: _FakeRedisClient) -> None:
        self._client = client

    class Redis:
        _client: _FakeRedisClient

        @classmethod
        def from_url(cls, _redis_url: str, *, decode_responses: bool) -> _FakeRedisClient:
            assert decode_responses is True
            return cls._client

    def bind(self) -> None:
        self.Redis._client = self._client


def _bind_fake_redis_for_cache(monkeypatch: pytest.MonkeyPatch, client: _FakeRedisClient) -> None:
    fake_module = _FakeRedisModule(client)
    fake_module.bind()
    monkeypatch.setattr(redis_cache_module, "_load_redis_module", lambda: fake_module)


def _bind_fake_redis_for_coordination(
    monkeypatch: pytest.MonkeyPatch, client: _FakeRedisClient
) -> None:
    fake_module = _FakeRedisModule(client)
    fake_module.bind()
    monkeypatch.setattr(redis_coord_module, "_load_redis_module", lambda: fake_module)


def test_redis_cache_store_is_v2_only(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeRedisClient()
    _bind_fake_redis_for_cache(monkeypatch, client)

    with pytest.raises(ValueError):
        redis_cache_module.RedisCacheStore(redis_url="redis://localhost:6379/0", namespace="dietary", keyspace_version="v1")

    store = redis_cache_module.RedisCacheStore(redis_url="redis://localhost:6379/0", namespace="dietary")
    assert store._key("reminders.ready") == "dietary:cache:reminder:reminders.ready"


def test_redis_cache_store_get_json_does_not_fallback_to_legacy_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeRedisClient()
    _bind_fake_redis_for_cache(monkeypatch, client)
    store = redis_cache_module.RedisCacheStore(redis_url="redis://localhost:6379/0", namespace="dietary")

    value = store.get_json("workers.ready")

    assert value is None
    assert client.get_calls == ["dietary:cache:general:workers.ready"]


def test_redis_coordination_store_v2_signal_paths_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeRedisClient()
    _bind_fake_redis_for_coordination(monkeypatch, client)
    store = redis_coord_module.RedisCoordinationStore(redis_url="redis://localhost:6379/0", namespace="dietary")

    v2_channel = "dietary:coordination:signal:reminder:reminders.ready"
    legacy_channel = "dietary:signal:reminders.ready"
    client._lists[v2_channel] = [json.dumps({"id": 1})]
    client._lists[legacy_channel] = [json.dumps({"id": 99})]
    drained = store.drain_signals("reminders.ready")

    assert drained == [{"id": 1}]
    assert client.rpop_calls == [v2_channel, v2_channel]
    assert legacy_channel in client._lists and client._lists[legacy_channel] == [json.dumps({"id": 99})]


def test_redis_coordination_store_wait_for_signal_no_legacy_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeRedisClient()
    _bind_fake_redis_for_coordination(monkeypatch, client)
    store = redis_coord_module.RedisCoordinationStore(redis_url="redis://localhost:6379/0", namespace="dietary")
    client._brpop_result = None

    payload = store.wait_for_signal("workers.ready", timeout_seconds=0.2)

    assert payload is None
    assert client.brpop_calls == [("dietary:coordination:signal:workflow:workers.ready", 1)]
