from __future__ import annotations

from dataclasses import dataclass

from collections.abc import Sequence

from care_pilot.core.events import DomainEvent
from care_pilot.platform.cache import EventTimelineService
from care_pilot.platform.eventing import (
    DeliverySemantics,
    EventHandlerCursorRecord,
    EventProjectionRegistry,
    EventReactionRegistry,
    ExecutionStatus,
    OrderingScope,
    ReactionExecutionRecord,
)
from care_pilot.platform.eventing.runner import run_eventing_once


class _InMemoryEventingStore:
    def __init__(self) -> None:
        self.records: dict[tuple[str, str], ReactionExecutionRecord] = {}
        self.cursors: dict[tuple[str, str], EventHandlerCursorRecord] = {}

    def save_reaction_execution(self, record: ReactionExecutionRecord) -> ReactionExecutionRecord:
        self.records[(record.event_id, record.handler_name)] = record
        return record

    def get_reaction_execution(
        self, *, event_id: str, handler_name: str
    ) -> ReactionExecutionRecord | None:
        return self.records.get((event_id, handler_name))

    def upsert_snapshot_section(self, record):  # pragma: no cover - not used
        return record

    def get_snapshot_section(self, *, user_id: str, section_key: str):  # pragma: no cover
        return None

    def list_snapshot_sections(self, *, user_id: str):  # pragma: no cover
        return []

    def upsert_event_handler_cursor(self, record: EventHandlerCursorRecord) -> EventHandlerCursorRecord:
        self.cursors[(record.handler_name, record.scope_key)] = record
        return record

    def get_event_handler_cursor(
        self, *, handler_name: str, scope_key: str
    ) -> EventHandlerCursorRecord | None:
        return self.cursors.get((handler_name, scope_key))

    def list_event_handler_cursors(self) -> list[EventHandlerCursorRecord]:
        return list(self.cursors.values())


@dataclass(slots=True)
class _CountingReaction:
    name: str
    event_types: Sequence[str]
    delivery_semantics: DeliverySemantics
    ordering_scope: OrderingScope
    count: int = 0

    def handle(self, event: DomainEvent) -> None:
        self.count += 1


@dataclass(slots=True)
class _CountingProjection:
    name: str
    event_types: Sequence[str]
    projection_section: str
    projection_version: str
    ordering_scope: OrderingScope
    count: int = 0

    def apply(self, event: DomainEvent) -> None:
        self.count += 1


def test_reaction_runs_once_per_event() -> None:
    event_timeline = EventTimelineService()
    record = event_timeline.append(
        event_type="agent_action_proposed",
        workflow_name="test",
        correlation_id="corr",
        request_id="req",
        user_id="user-1",
        payload={"agent_name": "test"},
    )

    reaction = _CountingReaction(
        name="counting",
        event_types=["agent_action_proposed"],
        delivery_semantics=DeliverySemantics.AT_LEAST_ONCE,
        ordering_scope=OrderingScope.NONE,
    )
    reaction_registry = EventReactionRegistry()
    reaction_registry.register(reaction)
    projection_registry = EventProjectionRegistry()
    store = _InMemoryEventingStore()

    run_eventing_once(
        event_timeline=event_timeline,
        eventing_store=store,
        reaction_registry=reaction_registry,
        projection_registry=projection_registry,
    )
    run_eventing_once(
        event_timeline=event_timeline,
        eventing_store=store,
        reaction_registry=reaction_registry,
        projection_registry=projection_registry,
    )

    assert reaction.count == 1
    execution = store.get_reaction_execution(event_id=record.event_id, handler_name="counting")
    assert execution is not None
    assert execution.status == ExecutionStatus.SUCCEEDED
    cursor = store.get_event_handler_cursor(handler_name="counting", scope_key="none")
    assert cursor is not None


def test_projection_skips_when_lock_unavailable() -> None:
    class _LockDenyStore:
        def acquire_lock(self, *args, **kwargs):  # noqa: ANN001
            return False

        def release_lock(self, *args, **kwargs):  # noqa: ANN001
            return None

    event_timeline = EventTimelineService()
    event_timeline.append(
        event_type="meal_analyzed",
        workflow_name="test",
        correlation_id="corr",
        request_id="req",
        user_id="user-1",
        payload={"status": "ok"},
    )
    projection = _CountingProjection(
        name="snapshot_projector",
        event_types=["meal_analyzed"],
        projection_section="patient_case_snapshot",
        projection_version="v1",
        ordering_scope=OrderingScope.PER_PATIENT,
    )
    projection_registry = EventProjectionRegistry()
    projection_registry.register(projection)
    reaction_registry = EventReactionRegistry()
    store = _InMemoryEventingStore()

    run_eventing_once(
        event_timeline=event_timeline,
        eventing_store=store,
        reaction_registry=reaction_registry,
        projection_registry=projection_registry,
        coordination_store=_LockDenyStore(),
    )

    assert projection.count == 0
    cursor = store.get_event_handler_cursor(handler_name="snapshot_projector", scope_key="user-1")
    assert cursor is None
