from dataclasses import dataclass, field
from threading import Lock
from typing import TYPE_CHECKING, cast

from apps.api.dietary_api.schemas import (
    NotificationItem,
    NotificationListResponse,
    NotificationMarkAllReadResponse,
    NotificationMarkReadResponse,
)
from dietary_guardian.models.workflow import WorkflowTimelineEvent

if TYPE_CHECKING:
    from apps.api.dietary_api.deps import AppContext


@dataclass
class NotificationReadStateStore:
    _read_by_user: dict[str, set[str]] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def is_read(self, *, user_id: str, notification_id: str) -> bool:
        with self._lock:
            return notification_id in self._read_by_user.get(user_id, set())

    def mark_read(self, *, user_id: str, notification_id: str) -> None:
        with self._lock:
            self._read_by_user.setdefault(user_id, set()).add(notification_id)

    def mark_all(self, *, user_id: str, notification_ids: list[str]) -> int:
        with self._lock:
            existing = self._read_by_user.setdefault(user_id, set())
            before = len(existing)
            existing.update(notification_ids)
            return len(existing) - before


def _category_for_event(event: WorkflowTimelineEvent) -> str:
    workflow_name = str(event.workflow_name or "")
    if workflow_name == "meal_analysis":
        return "meal_analysis"
    if workflow_name == "alert_only":
        return "alerts"
    if workflow_name == "replay":
        return "workflow_replay"
    return "workflow"


def _title_for_event(event: WorkflowTimelineEvent) -> str:
    workflow_name = str(event.workflow_name or "")
    if workflow_name == "meal_analysis":
        return "Meal Analysis Completed"
    if workflow_name == "alert_only":
        return "Alert Workflow Completed"
    if workflow_name == "replay":
        return "Workflow Replay Viewed"
    return "Workflow Update"


def _message_for_event(event: WorkflowTimelineEvent) -> str:
    payload = cast(dict[str, object], event.payload)
    workflow_name = str(event.workflow_name or "")
    if workflow_name == "meal_analysis":
        dish = str(payload.get("dish_name") or "meal")
        manual_review = bool(payload.get("manual_review"))
        suffix = " (manual review suggested)" if manual_review else ""
        return f"Meal analysis completed for {dish}{suffix}"
    if workflow_name == "alert_only":
        success = bool(payload.get("tool_success"))
        return "Alert delivery workflow completed successfully" if success else "Alert workflow completed with issues"
    return f"{event.event_type.replace('_', ' ').title()} in {workflow_name or 'workflow'}"


def _notification_from_event(*, event: WorkflowTimelineEvent, reads: NotificationReadStateStore, user_id: str) -> NotificationItem:
    notification_id = event.event_id
    return NotificationItem(
        id=notification_id,
        event_id=event.event_id,
        event_type=event.event_type,
        workflow_name=str(event.workflow_name) if event.workflow_name is not None else None,
        category=_category_for_event(event),
        title=_title_for_event(event),
        message=_message_for_event(event),
        created_at=event.created_at,
        correlation_id=event.correlation_id,
        request_id=event.request_id,
        user_id=event.user_id,
        read=reads.is_read(user_id=user_id, notification_id=notification_id),
    )


def _user_notification_events(*, context: "AppContext", user_id: str) -> list[WorkflowTimelineEvent]:
    events = context.event_timeline.list(user_id=user_id)
    return [event for event in events if event.event_type == "workflow_completed"]


def list_notifications(*, context: "AppContext", user_id: str) -> NotificationListResponse:
    events = _user_notification_events(context=context, user_id=user_id)
    items = [
        _notification_from_event(event=event, reads=context.notification_reads, user_id=user_id)
        for event in reversed(events)
    ]
    unread_count = sum(1 for item in items if not item.read)
    return NotificationListResponse(items=items, unread_count=unread_count)


def mark_notification_read(
    *,
    context: "AppContext",
    user_id: str,
    notification_id: str,
) -> NotificationMarkReadResponse | None:
    existing = list_notifications(context=context, user_id=user_id)
    current = next((item for item in existing.items if item.id == notification_id), None)
    if current is None:
        return None
    context.notification_reads.mark_read(user_id=user_id, notification_id=notification_id)
    refreshed = list_notifications(context=context, user_id=user_id)
    updated = next(item for item in refreshed.items if item.id == notification_id)
    return NotificationMarkReadResponse(notification=updated, unread_count=refreshed.unread_count)


def mark_all_notifications_read(*, context: "AppContext", user_id: str) -> NotificationMarkAllReadResponse:
    existing = list_notifications(context=context, user_id=user_id)
    updated_count = context.notification_reads.mark_all(
        user_id=user_id,
        notification_ids=[item.id for item in existing.items],
    )
    refreshed = list_notifications(context=context, user_id=user_id)
    return NotificationMarkAllReadResponse(updated_count=updated_count, unread_count=refreshed.unread_count)
