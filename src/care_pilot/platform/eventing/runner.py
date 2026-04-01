"""Run projection and reaction handlers over the event timeline."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from care_pilot.core.events import DomainEvent
from care_pilot.platform.cache.timeline_service import EventTimelineService
from care_pilot.platform.eventing.models import (
    EventHandlerCursorRecord,
    ExecutionStatus,
    ReactionExecutionRecord,
)
from care_pilot.platform.eventing.registry import EventProjectionRegistry, EventReactionRegistry
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class EventingRunResult:
    projections_applied: int = 0
    projections_skipped: int = 0
    reactions_attempted: int = 0
    reactions_succeeded: int = 0
    reactions_failed: int = 0


def _to_domain_event(timeline_event) -> DomainEvent:  # noqa: ANN001
    payload = {
        "data": timeline_event.payload,
        "meta": {
            "event_id": timeline_event.event_id,
            "correlation_id": timeline_event.correlation_id,
            "request_id": timeline_event.request_id,
            "workflow_name": timeline_event.workflow_name,
            "user_id": timeline_event.user_id,
        },
    }
    return DomainEvent(
        event_type=timeline_event.event_type,
        payload=payload,
        occurred_at=timeline_event.created_at,
    )


def _payload_hash(event: DomainEvent) -> str:
    payload_json = json.dumps(event.payload, sort_keys=True, default=str)
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _acquire_ordering_lock(
    *, coordination_store, lock_key: str, owner: str, ttl_seconds: int
) -> bool:
    if coordination_store is None:
        return True
    acquire = getattr(coordination_store, "acquire_lock", None)
    if not callable(acquire):
        return True
    return bool(acquire(lock_key, owner=owner, ttl_seconds=ttl_seconds))


def _release_ordering_lock(*, coordination_store, lock_key: str, owner: str) -> None:
    if coordination_store is None:
        return
    release = getattr(coordination_store, "release_lock", None)
    if callable(release):
        release(lock_key, owner=owner)


def _scope_key_for_event(handler, event: DomainEvent) -> str | None:
    meta = event.payload.get("meta", {}) if isinstance(event.payload, dict) else {}
    user_id = meta.get("user_id")
    correlation_id = meta.get("correlation_id")
    if handler.ordering_scope.value == "global":
        return "global"
    if handler.ordering_scope.value == "per_patient":
        return str(user_id) if user_id else None
    if handler.ordering_scope.value == "per_case":
        return str(correlation_id) if correlation_id else None
    return "none"


MAX_REACTION_RETRIES = 5
REACTION_RETRY_BACKOFF_MINUTES = [1, 5, 15, 60, 240]  # Exponential-ish backoff


def _execute_reaction(
    *,
    event_id: str,
    handler,
    event: DomainEvent,
    eventing_store,
    coordination_store,
    lease_owner: str,
    lease_seconds: int,
) -> bool:
    existing = eventing_store.get_reaction_execution(event_id=event_id, handler_name=handler.name)

    if existing is not None:
        if existing.status == ExecutionStatus.SUCCEEDED:
            return True
        if existing.status == ExecutionStatus.DEAD_LETTER:
            return True
        if (
            existing.status == ExecutionStatus.FAILED
            and existing.next_retry_at
            and datetime.now(UTC) < existing.next_retry_at
        ):
            return False

    meta = event.payload.get("meta", {}) if isinstance(event.payload, dict) else {}
    user_id = meta.get("user_id")
    correlation_id = meta.get("correlation_id")
    lock_key = None
    if handler.ordering_scope.value == "global":
        lock_key = f"eventing:reaction:{handler.name}:global"
    elif handler.ordering_scope.value == "per_patient":
        if not user_id:
            return False
        lock_key = f"eventing:reaction:{handler.name}:patient:{user_id}"
    elif handler.ordering_scope.value == "per_case":
        if not correlation_id:
            return False
        lock_key = f"eventing:reaction:{handler.name}:case:{correlation_id}"

    if lock_key is not None and not _acquire_ordering_lock(
        coordination_store=coordination_store,
        lock_key=lock_key,
        owner=lease_owner,
        ttl_seconds=lease_seconds,
    ):
        return False

    now = datetime.now(UTC)
    failure_count = existing.failure_count if existing is not None else 0
    payload_hash = _payload_hash(event)
    event_version = meta.get("event_version") if isinstance(meta, dict) else None
    record = ReactionExecutionRecord(
        event_id=event_id,
        handler_name=handler.name,
        status=ExecutionStatus.RUNNING,
        started_at=now,
        failure_count=failure_count,
        payload_hash=payload_hash,
        event_version=event_version,
        ordering_scope=handler.ordering_scope,
    )
    eventing_store.save_reaction_execution(record)
    try:
        handler.handle(event)
    except Exception as exc:  # noqa: BLE001
        failure_count += 1
        status = ExecutionStatus.FAILED
        next_retry_at = None

        if failure_count >= MAX_REACTION_RETRIES:
            status = ExecutionStatus.DEAD_LETTER
            logger.error(
                "event_reaction_dead_letter handler=%s event_id=%s failure_count=%s",
                handler.name,
                event_id,
                failure_count,
            )
        else:
            backoff_idx = min(failure_count - 1, len(REACTION_RETRY_BACKOFF_MINUTES) - 1)
            minutes = REACTION_RETRY_BACKOFF_MINUTES[backoff_idx]
            from datetime import timedelta

            next_retry_at = datetime.now(UTC) + timedelta(minutes=minutes)
            logger.warning(
                "event_reaction_retry_scheduled handler=%s event_id=%s failure_count=%s next_retry=%s",
                handler.name,
                event_id,
                failure_count,
                next_retry_at,
            )

        failed_record = ReactionExecutionRecord(
            event_id=event_id,
            handler_name=handler.name,
            status=status,
            started_at=record.started_at,
            completed_at=datetime.now(UTC),
            failure_count=failure_count,
            last_error=str(exc),
            payload_hash=payload_hash,
            event_version=event_version,
            ordering_scope=handler.ordering_scope,
            next_retry_at=next_retry_at,
        )
        eventing_store.save_reaction_execution(failed_record)
        if lock_key is not None:
            _release_ordering_lock(
                coordination_store=coordination_store, lock_key=lock_key, owner=lease_owner
            )
        return False

    succeeded_record = ReactionExecutionRecord(
        event_id=event_id,
        handler_name=handler.name,
        status=ExecutionStatus.SUCCEEDED,
        started_at=record.started_at,
        completed_at=datetime.now(UTC),
        failure_count=failure_count,
        payload_hash=payload_hash,
        event_version=event_version,
        ordering_scope=handler.ordering_scope,
    )
    eventing_store.save_reaction_execution(succeeded_record)
    if lock_key is not None:
        _release_ordering_lock(
            coordination_store=coordination_store, lock_key=lock_key, owner=lease_owner
        )
    return True


def _execute_projection(
    *,
    handler,
    event: DomainEvent,
    coordination_store,
    lease_owner: str,
    lease_seconds: int,
) -> bool:
    scope_key = _scope_key_for_event(handler, event)
    if scope_key is None:
        return False
    lock_key = None
    if handler.ordering_scope.value == "global":
        lock_key = f"eventing:projection:{handler.name}:global"
    elif handler.ordering_scope.value == "per_patient":
        lock_key = f"eventing:projection:{handler.name}:patient:{scope_key}"
    elif handler.ordering_scope.value == "per_case":
        lock_key = f"eventing:projection:{handler.name}:case:{scope_key}"

    if lock_key is not None and not _acquire_ordering_lock(
        coordination_store=coordination_store,
        lock_key=lock_key,
        owner=lease_owner,
        ttl_seconds=lease_seconds,
    ):
        return False
    try:
        handler.apply(event)
    except Exception:  # noqa: BLE001
        logger.exception(
            "event_projection_failed handler=%s event_id=%s",
            handler.name,
            event.payload.get("meta", {}).get("event_id")
            if isinstance(event.payload, dict)
            else None,
        )
        if lock_key is not None:
            _release_ordering_lock(
                coordination_store=coordination_store, lock_key=lock_key, owner=lease_owner
            )
        return False
    if lock_key is not None:
        _release_ordering_lock(
            coordination_store=coordination_store, lock_key=lock_key, owner=lease_owner
        )
    return True


def run_eventing_once(
    *,
    event_timeline: EventTimelineService,
    eventing_store,
    reaction_registry: EventReactionRegistry,
    projection_registry: EventProjectionRegistry,
    coordination_store=None,
    lease_owner: str = "eventing",
    lease_seconds: int = 30,
) -> EventingRunResult:
    result = EventingRunResult()
    cursor_times = [
        cursor.last_event_time
        for cursor in eventing_store.list_event_handler_cursors()
        if cursor.last_event_time is not None
    ]
    since_time = min(cursor_times) if cursor_times else None

    events = event_timeline.get_events(since_time=since_time)
    for timeline_event in events:
        domain_event = _to_domain_event(timeline_event)
        for projection in projection_registry.handlers_for(timeline_event.event_type):
            scope_key = _scope_key_for_event(projection, domain_event)
            if scope_key is None:
                continue
            cursor = eventing_store.get_event_handler_cursor(
                handler_name=projection.name,
                scope_key=scope_key,
            )
            if (
                cursor
                and cursor.last_event_time
                and timeline_event.created_at <= cursor.last_event_time
            ):
                continue
            if _execute_projection(
                handler=projection,
                event=domain_event,
                coordination_store=coordination_store,
                lease_owner=lease_owner,
                lease_seconds=lease_seconds,
            ):
                result.projections_applied += 1
                eventing_store.upsert_event_handler_cursor(
                    EventHandlerCursorRecord(
                        handler_name=projection.name,
                        scope_key=scope_key,
                        last_event_id=timeline_event.event_id,
                        last_event_time=timeline_event.created_at,
                    )
                )
            else:
                result.projections_skipped += 1

        for reaction in reaction_registry.handlers_for(timeline_event.event_type):
            scope_key = _scope_key_for_event(reaction, domain_event)
            if scope_key is None:
                continue
            cursor = eventing_store.get_event_handler_cursor(
                handler_name=reaction.name,
                scope_key=scope_key,
            )
            if (
                cursor
                and cursor.last_event_time
                and timeline_event.created_at <= cursor.last_event_time
            ):
                continue
            result.reactions_attempted += 1
            succeeded = _execute_reaction(
                event_id=timeline_event.event_id,
                handler=reaction,
                event=domain_event,
                eventing_store=eventing_store,
                coordination_store=coordination_store,
                lease_owner=lease_owner,
                lease_seconds=lease_seconds,
            )
            if succeeded:
                result.reactions_succeeded += 1
                eventing_store.upsert_event_handler_cursor(
                    EventHandlerCursorRecord(
                        handler_name=reaction.name,
                        scope_key=scope_key,
                        last_event_id=timeline_event.event_id,
                        last_event_time=timeline_event.created_at,
                    )
                )
            else:
                result.reactions_failed += 1

    return result


def run_projection_replay(
    *,
    event_timeline: EventTimelineService,
    eventing_store,
    projection_registry: EventProjectionRegistry,
    coordination_store=None,
    lease_owner: str = "projection-replay",
    lease_seconds: int = 30,
    user_id: str | None = None,
    since_time: datetime | None = None,
) -> EventingRunResult:
    result = EventingRunResult()
    events = event_timeline.get_events(user_id=user_id, since_time=since_time)
    for timeline_event in events:
        domain_event = _to_domain_event(timeline_event)
        for projection in projection_registry.handlers_for(timeline_event.event_type):
            scope_key = _scope_key_for_event(projection, domain_event)
            if scope_key is None:
                result.projections_skipped += 1
                continue
            if _execute_projection(
                handler=projection,
                event=domain_event,
                coordination_store=coordination_store,
                lease_owner=lease_owner,
                lease_seconds=lease_seconds,
            ):
                result.projections_applied += 1
                eventing_store.upsert_event_handler_cursor(
                    EventHandlerCursorRecord(
                        handler_name=projection.name,
                        scope_key=scope_key,
                        last_event_id=timeline_event.event_id,
                        last_event_time=timeline_event.created_at,
                    )
                )
            else:
                result.projections_skipped += 1
    return result


__all__ = ["EventingRunResult", "run_eventing_once", "run_projection_replay"]
