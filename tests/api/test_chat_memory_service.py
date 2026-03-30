"""Unit tests for chat memory context formatting."""

from __future__ import annotations

from care_pilot.features.companion.chat.memory_store import build_memory_context
from care_pilot.platform.memory import MemorySnippet


def test_build_memory_context_renders_top_k() -> None:
    snippets = [
        MemorySnippet(text="Prefers low sodium meals", score=0.91),
        MemorySnippet(text="Allergic to peanuts", score=0.88),
    ]
    context = build_memory_context(snippets)
    assert "Relevant memories" in context
    assert "Prefers low sodium meals" in context
    assert "Allergic to peanuts" in context
