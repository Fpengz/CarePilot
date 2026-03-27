"""Eventing contracts for projections and reactions.

These contracts formalize the separation between domain events (facts),
projections (deterministic state maintenance), and reactions (optional
side-effectful enrichments).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from care_pilot.core.events import DomainEvent


class DeliverySemantics(StrEnum):
    AT_LEAST_ONCE = "at_least_once"


class OrderingScope(StrEnum):
    GLOBAL = "global"
    PER_PATIENT = "per_patient"
    PER_CASE = "per_case"
    NONE = "none"


class EventReactionHandler(Protocol):
    name: str
    event_types: Sequence[str]
    delivery_semantics: DeliverySemantics
    ordering_scope: OrderingScope

    def handle(self, event: DomainEvent) -> None: ...


class EventProjectionHandler(Protocol):
    name: str
    event_types: Sequence[str]
    projection_section: str
    projection_version: str
    ordering_scope: OrderingScope

    def apply(self, event: DomainEvent) -> None: ...


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass(slots=True)
class ReactionExecutionRecord:
    event_id: str
    handler_name: str
    status: ExecutionStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failure_count: int = 0
    last_error: str | None = None
    payload_hash: str | None = None
    event_version: str | None = None
    ordering_scope: OrderingScope = OrderingScope.NONE
    next_retry_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class SnapshotSectionRecord:
    user_id: str
    section_key: str
    payload: dict[str, object]
    schema_version: str
    projection_version: str
    source_event_cursor: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class EventHandlerCursorRecord:
    handler_name: str
    scope_key: str
    last_event_id: str | None = None
    last_event_time: datetime | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "DeliverySemantics",
    "ExecutionStatus",
    "EventProjectionHandler",
    "EventReactionHandler",
    "OrderingScope",
    "ReactionExecutionRecord",
    "SnapshotSectionRecord",
    "EventHandlerCursorRecord",
]
