#!/usr/bin/env python3
from __future__ import annotations

from collections.abc import Iterable

import typer


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


def main(
    redis_url: str = typer.Option(..., "--redis-url", help="Redis URL to migrate."),
    namespace: str = typer.Option("dietary_guardian", "--namespace", help="Redis key namespace."),
    apply: bool = typer.Option(False, "--apply", help="Apply key rename operations."),
) -> None:
    import redis

    client = redis.Redis.from_url(redis_url, decode_responses=True)
    patterns = (
        f"{namespace}:lock:*",
        f"{namespace}:signal:*",
        f"{namespace}:cache:*",
    )
    keys = _iter_keys(client, patterns)
    if not keys:
        typer.echo("No matching keys found.")
        raise typer.Exit(code=0)

    typer.echo(f"Found {len(keys)} key(s).")
    for old_key in keys:
        new_key = _new_key(namespace, old_key)
        if new_key is None:
            continue
        if new_key == old_key:
            continue
        typer.echo(f"{old_key} -> {new_key}")
        if apply:
            client.rename(old_key, new_key)
    if not apply:
        typer.echo("Dry run only. Re-run with --apply to perform migration.")


if __name__ == "__main__":
    typer.run(main)
