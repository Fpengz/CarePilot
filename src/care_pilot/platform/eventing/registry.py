"""In-memory registries for event projections and reactions."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from care_pilot.platform.eventing.models import EventProjectionHandler, EventReactionHandler


class EventReactionRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventReactionHandler]] = defaultdict(list)

    def register(self, handler: EventReactionHandler) -> None:
        for event_type in handler.event_types:
            self._handlers[event_type].append(handler)

    def handlers_for(self, event_type: str) -> Sequence[EventReactionHandler]:
        return tuple(self._handlers.get(event_type, ()))

    def all_handlers(self) -> Sequence[EventReactionHandler]:
        aggregated: list[EventReactionHandler] = []
        for handlers in self._handlers.values():
            aggregated.extend(handlers)
        return tuple(aggregated)


class EventProjectionRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventProjectionHandler]] = defaultdict(list)

    def register(self, handler: EventProjectionHandler) -> None:
        for event_type in handler.event_types:
            self._handlers[event_type].append(handler)

    def handlers_for(self, event_type: str) -> Sequence[EventProjectionHandler]:
        return tuple(self._handlers.get(event_type, ()))

    def all_handlers(self) -> Sequence[EventProjectionHandler]:
        aggregated: list[EventProjectionHandler] = []
        for handlers in self._handlers.values():
            aggregated.extend(handlers)
        return tuple(aggregated)


__all__ = ["EventProjectionRegistry", "EventReactionRegistry"]
