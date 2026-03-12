"""
agents/search_agent.py
----------------------
Low-level DuckDuckGo search wrapper.

Provides a single `search()` primitive used by the route handlers.
Routing decisions (drug vs food vs general) are made by the LLM in
chat/router.py — this module has no opinion on what the query is about.
"""

from __future__ import annotations

from typing import NamedTuple

from ddgs import DDGS


class SearchResult(NamedTuple):
    title: str
    url: str
    body: str


class SearchAgent:
    """Thin wrapper around DuckDuckGo text search."""

    def __init__(self, max_results: int = 3, timeout: int = 10) -> None:
        self._max_results = max_results
        self._timeout = timeout

    def search(self, query: str) -> list[SearchResult]:
        """
        Search via ddgs metasearch and return up to max_results results.
        Uses sg-en region to bias results toward Singapore sources.
        Returns an empty list on any error (network, rate-limit, etc.).
        """
        try:
            with DDGS(timeout=self._timeout) as ddgs:
                raw = ddgs.text(
                    query,
                    region="sg-en",
                    max_results=self._max_results,
                    backend="auto",
                )
            return [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    body=r.get("body", ""),
                )
                for r in (raw or [])
            ]
        except Exception as exc:
            print(f"[SearchAgent] Search error: {exc}")
            return []
