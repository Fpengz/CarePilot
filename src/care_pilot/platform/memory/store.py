"""
Define memory storage contracts and Mem0-backed implementations.

This module keeps memory storage concerns in the platform layer, exposing
typed protocols for search and append operations without leaking provider
details into feature or API layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, cast

from care_pilot.config.app import AppSettings
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class MemorySnippet:
    """Small memory excerpt for prompt injection."""

    text: str
    score: float | None = None
    memory_id: str | None = None
    metadata: dict[str, object] | None = None


class MemoryStore(Protocol):
    """Minimal memory store contract for chat personalization."""

    @property
    def enabled(self) -> bool: ...

    def search(self, *, user_id: str, query: str, limit: int) -> list[MemorySnippet]: ...

    def add_messages(
        self,
        *,
        user_id: str,
        session_id: str,
        messages: list[dict[str, str]],
        metadata: dict[str, object] | None = None,
    ) -> None: ...


class NullMemoryStore:
    """No-op memory store used when Mem0 is disabled."""

    @property
    def enabled(self) -> bool:
        return False

    def search(self, *, user_id: str, query: str, limit: int) -> list[MemorySnippet]:
        return []

    def add_messages(
        self,
        *,
        user_id: str,
        session_id: str,
        messages: list[dict[str, str]],
        metadata: dict[str, object] | None = None,
    ) -> None:
        return None


class Mem0MemoryStore:
    """Mem0-backed memory store adapter."""

    def __init__(self, *, api_key: str, base_url: str | None = None) -> None:
        try:
            from mem0 import MemoryClient
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("mem0ai dependency is missing") from exc

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["host"] = base_url
            kwargs["base_url"] = base_url

        try:
            client_cls = cast(Any, MemoryClient)
            self._client = client_cls(**kwargs)
        except TypeError:
            kwargs.pop("base_url", None)
            kwargs.pop("host", None)
            client_cls = cast(Any, MemoryClient)
            self._client = client_cls(api_key=api_key)

        self._base_url = base_url

    @property
    def enabled(self) -> bool:
        return True

    def search(self, *, user_id: str, query: str, limit: int) -> list[MemorySnippet]:
        try:
            result = self._client.search(query, filters={"user_id": user_id}, top_k=limit)
        except TypeError:
            result = self._client.search(query, filters={"user_id": user_id})

        items: list[dict]
        if isinstance(result, dict):
            items = list(result.get("results", []))
        else:
            items = list(result)

        snippets: list[MemorySnippet] = []
        for raw in items[:limit]:
            item = cast(dict[str, object], raw)
            text = str(item.get("memory") or item.get("text") or "").strip()
            if not text:
                continue
            score = item.get("score")
            metadata = item.get("metadata")
            snippets.append(
                MemorySnippet(
                    text=text,
                    score=(float(score) if isinstance(score, (int, float, str)) else None),
                    memory_id=(str(item.get("id")) if item.get("id") is not None else None),
                    metadata=(
                        cast(dict[str, object], metadata) if isinstance(metadata, dict) else None
                    ),
                )
            )
        return snippets

    def add_messages(
        self,
        *,
        user_id: str,
        session_id: str,
        messages: list[dict[str, str]],
        metadata: dict[str, object] | None = None,
    ) -> None:
        payload = {"session_id": session_id}
        if metadata:
            payload.update(metadata)
        try:
            self._client.add(messages, user_id=user_id, metadata=payload)
        except TypeError:
            self._client.add(messages, user_id=user_id)


def build_memory_store(settings: AppSettings) -> MemoryStore:
    if not settings.memory.enabled or not settings.memory.api_key:
        return NullMemoryStore()
    try:
        return Mem0MemoryStore(
            api_key=settings.memory.api_key,
            base_url=settings.memory.base_url,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("mem0_init_failed error=%s", exc)
        return NullMemoryStore()


__all__ = [
    "MemorySnippet",
    "MemoryStore",
    "NullMemoryStore",
    "Mem0MemoryStore",
    "build_memory_store",
]
