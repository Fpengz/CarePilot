"""Reaction handlers for agent proposals and background enrichments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from care_pilot.core.events import DomainEvent
from care_pilot.platform.eventing.models import (
    DeliverySemantics,
    EventReactionHandler,
    OrderingScope,
)
from care_pilot.platform.observability.setup import get_logger

logger = get_logger(__name__)


def _ttl_seconds_for_agent(agent_name: str | None) -> int:
    if not agent_name:
        return 3600
    lowered = agent_name.lower()
    if "emotion" in lowered:
        return 15 * 60
    if "adherence" in lowered:
        return 2 * 60 * 60
    if "trend" in lowered:
        return 6 * 60 * 60
    if "care" in lowered or "plan" in lowered:
        return 60 * 60
    return 2 * 60 * 60


@dataclass(slots=True)
class AgentProposalCacheReaction(EventReactionHandler):
    name: str
    event_types: list[str]
    delivery_semantics: DeliverySemantics
    ordering_scope: OrderingScope
    cache_store: object

    def handle(self, event: DomainEvent) -> None:
        payload = event.payload if isinstance(event.payload, dict) else {}
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
        agent_name = data.get("agent_name") if isinstance(data, dict) else None
        ttl_seconds = _ttl_seconds_for_agent(str(agent_name) if agent_name else None)
        key = f"agent_proposal:{meta.get('event_id', '')}:{agent_name or 'unknown'}"
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        cache_payload = {
            "agent_name": agent_name,
            "payload": data,
            "event_meta": meta,
            "expires_at": expires_at.isoformat(),
        }
        setter = getattr(self.cache_store, "set_json", None)
        if callable(setter):
            setter(key, cache_payload, ttl_seconds=ttl_seconds)
        logger.info(
            "agent_proposal_cached key=%s ttl_seconds=%s",
            key,
            ttl_seconds,
        )


__all__ = ["AgentProposalCacheReaction"]
