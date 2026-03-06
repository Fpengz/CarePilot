#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections.abc import Iterable


def _domain(value: str) -> str:
    lowered = value.lower()
    if "reminder" in lowered:
        return "reminder"
    if "outbox" in lowered or "workflow" in lowered or "worker" in lowered:
        return "workflow"
    if "notification" in lowered:
        return "notification"
    return "coordination"


def _cache_domain(value: str) -> str:
    lowered = value.lower()
    if "reminder" in lowered:
        return "reminder"
    if "notification" in lowered:
        return "notification"
    if "workflow" in lowered or "outbox" in lowered:
        return "workflow"
    return "general"


def _iter_keys(client: object, patterns: Iterable[str]) -> list[str]:
    keys: list[str] = []
    redis_client = client
    for pattern in patterns:
        cursor = 0
        while True:
            cursor, values = redis_client.scan(cursor=cursor, match=pattern, count=200)  # type: ignore[attr-defined]
            keys.extend(str(value) for value in values)
            if cursor == 0:
                break
    return sorted(set(keys))


def _new_key(namespace: str, old_key: str) -> str | None:
    lock_prefix = f"{namespace}:lock:"
    signal_prefix = f"{namespace}:signal:"
    cache_prefix = f"{namespace}:cache:"
    if old_key.startswith(lock_prefix):
        suffix = old_key.removeprefix(lock_prefix)
        return f"{namespace}:coordination:lock:{_domain(suffix)}:{suffix}"
    if old_key.startswith(signal_prefix):
        suffix = old_key.removeprefix(signal_prefix)
        return f"{namespace}:coordination:signal:{_domain(suffix)}:{suffix}"
    if old_key.startswith(cache_prefix):
        suffix = old_key.removeprefix(cache_prefix)
        return f"{namespace}:cache:{_cache_domain(suffix)}:{suffix}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate Redis keyspace from v1 to v2 naming")
    parser.add_argument("--redis-url", required=True)
    parser.add_argument("--namespace", default="dietary_guardian")
    parser.add_argument("--apply", action="store_true", help="Apply key rename operations")
    args = parser.parse_args()

    import redis

    client = redis.Redis.from_url(args.redis_url, decode_responses=True)
    patterns = (
        f"{args.namespace}:lock:*",
        f"{args.namespace}:signal:*",
        f"{args.namespace}:cache:*",
    )
    keys = _iter_keys(client, patterns)
    if not keys:
        print("No matching keys found.")
        return 0

    print(f"Found {len(keys)} key(s).")
    for old_key in keys:
        new_key = _new_key(args.namespace, old_key)
        if new_key is None:
            continue
        if new_key == old_key:
            continue
        print(f"{old_key} -> {new_key}")
        if args.apply:
            client.rename(old_key, new_key)
    if not args.apply:
        print("Dry run only. Re-run with --apply to perform migration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
