"""
Define shared route contracts for the chat router.

This module contains the base route result model used by individual
route handlers that enrich chat context.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class RouteResult:
    """Returned by every route handler."""
    route_name: str              # "drug", "food", or "general"
    context: str | None          # injected as system context to the LLM (None = no enrichment)
    metadata: dict = field(default_factory=dict)  # optional debug info


class BaseRoute:
    """Every route must implement enrich()."""

    def enrich(self, text: str) -> RouteResult:
        """Fetch enriched context for the given query and return a RouteResult."""
        raise NotImplementedError
