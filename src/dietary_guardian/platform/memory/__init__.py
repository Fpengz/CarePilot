"""
Provide external memory storage adapters for chat personalization.

This module defines the MemoryStore protocol and concrete adapters that
bridge to external memory services (Mem0) or no-op fallbacks.
"""

from .store import MemorySnippet, MemoryStore, NullMemoryStore, build_memory_store

__all__ = ["MemorySnippet", "MemoryStore", "NullMemoryStore", "build_memory_store"]
