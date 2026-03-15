"""
Provide Mem0-backed chat memory helpers.

This module formats retrieved memories for prompt injection and records
chat turns into the configured MemoryStore implementation.
"""

from __future__ import annotations

import asyncio

from care_pilot.platform.memory import MemorySnippet, MemoryStore
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


def build_memory_context(snippets: list[MemorySnippet]) -> str:
    """Render memory snippets into a compact context block."""
    lines = ["Relevant memories:"]
    for snippet in snippets:
        text = snippet.text.strip()
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines)


async def fetch_memory_snippets(
    *,
    memory_store: MemoryStore,
    user_id: str,
    query: str,
    limit: int,
) -> list[MemorySnippet]:
    if not memory_store.enabled:
        return []
    try:
        return await asyncio.to_thread(
            memory_store.search,
            user_id=user_id,
            query=query,
            limit=limit,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("chat_memory_search_failed error=%s", exc)
        return []


async def record_chat_turn(
    *,
    memory_store: MemoryStore,
    user_id: str,
    session_id: str,
    user_message: str,
    assistant_message: str,
    metadata: dict[str, object] | None = None,
) -> None:
    if not memory_store.enabled:
        return
    messages = [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": assistant_message},
    ]
    try:
        await asyncio.to_thread(
            memory_store.add_messages,
            user_id=user_id,
            session_id=session_id,
            messages=messages,
            metadata=metadata,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("chat_memory_write_failed error=%s", exc)
