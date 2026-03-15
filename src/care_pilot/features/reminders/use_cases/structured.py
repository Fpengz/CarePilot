"""Structured reminder use cases."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from apps.api.carepilot_api.routes_shared import default_demo_regimens
from care_pilot.features.companion.core.health.models import (
    MedicationAdherenceEvent,
)
from care_pilot.features.companion.core.health.analytics import (
    EngagementMetrics,
)
from care_pilot.features.medications.domain import compute_mcr
from care_pilot.features.profiles.domain.models import UserProfile
from care_pilot.features.reminders.domain.generation import (
    definition_from_regimen,
    occurrences_for_definition,
)
from care_pilot.features.reminders.domain.models import (
    ReminderActionRecord,
    ReminderDefinition,
    ReminderEvent,
    ReminderOccurrence,
    ReminderNotificationLogEntry,
)
from care_pilot.features.reminders.notifications.reminder_materialization import (
    cancel_reminder_notifications,
    materialize_reminder_notifications,
)
from care_pilot.platform.auth.session_context import (
    build_user_profile_from_session,
)

if TYPE_CHECKING:
    from apps.api.carepilot_api.deps import AppContext


def _definition_summary(definition: ReminderDefinition) -> str:
    parts = [
        definition.medication_name,
        definition.dosage_text,
        definition.instructions_text or "",
    ]
    return ", ".join(part for part in parts if part)


def _find_definition_for_regimen(
    *, context: "AppContext", user_id: str, regimen_id: str
) -> ReminderDefinition | None:
    for item in context.stores.reminders.list_reminder_definitions(
        user_id, active_only=False
    ):
        if item.regimen_id == regimen_id:
            return item
    return None


def _event_from_occurrence(
    definition: ReminderDefinition, occurrence: ReminderOccurrence
) -> ReminderEvent:
    return ReminderEvent(
        id=occurrence.id,
        user_id=definition.user_id,
        reminder_definition_id=definition.id,
        occurrence_id=occurrence.id,
        regimen_id=definition.regimen_id,
        reminder_type=definition.reminder_type,
        title=definition.title,
        body=definition.body or _definition_summary(definition),
        medication_name=definition.medication_name,
        scheduled_at=occurrence.scheduled_for,
        dosage_text=definition.dosage_text,
        status=(
            "acknowledged"
            if occurrence.status == "completed"
            else ("missed" if occurrence.status == "missed" else "sent")
        ),
        meal_confirmation=(
            "yes"
            if occurrence.action == "taken"
            else ("no" if occurrence.action == "skipped" else "unknown")
        ),
        ack_at=occurrence.acted_at,
    )


def _upsert_definition_from_regimen(
    *,
    context: "AppContext",
    regimen,
) -> ReminderDefinition:
    existing = _find_definition_for_regimen(
        context=context, user_id=regimen.user_id, regimen_id=regimen.id
    )
    candidate = definition_from_regimen(regimen)
    if existing is not None:
        candidate.id = existing.id
        candidate.created_at = existing.created_at
    return context.stores.reminders.save_reminder_definition(candidate)


def _existing_occurrence_keys(
    *, context: "AppContext", user_id: str
) -> set[tuple[str, str]]:
    items = context.stores.reminders.list_reminder_occurrences(
        user_id=user_id, limit=1000
    )
    return {
        (item.reminder_definition_id, item.scheduled_for.isoformat())
        for item in items
    }


def _sync_occurrence_projection(
    *,
    context: "AppContext",
    definition: ReminderDefinition,
    occurrence: ReminderOccurrence,
) -> None:
    event = _event_from_occurrence(definition, occurrence)
    context.stores.reminders.save_reminder_event(event)
    materialize_reminder_notifications(
        repository=context.stores.reminders,
        reminder_event=event,
        reminder_type=event.reminder_type,
    )


def generate_structured_reminders_for_session(
    *,
    context: "AppContext",
    session: dict[str, object],
) -> tuple[list[ReminderEvent], EngagementMetrics]:
    user_profile: UserProfile = build_user_profile_from_session(
        session, context.stores.profiles
    )
    regimens = context.stores.medications.list_medication_regimens(
        user_profile.id, active_only=True
    )
    if not regimens:
        regimens = default_demo_regimens(user_profile.id)
        for item in regimens:
            context.stores.medications.save_medication_regimen(item)

    existing_keys = _existing_occurrence_keys(
        context=context, user_id=user_profile.id
    )
    created_events: list[ReminderEvent] = []
    target_date = datetime.now(timezone.utc).date()
    for regimen in regimens:
        definition = _upsert_definition_from_regimen(
            context=context, regimen=regimen
        )
        for occurrence in occurrences_for_definition(
            definition=definition,
            target_date=target_date,
            user_profile=user_profile,
        ):
            dedupe_key = (
                occurrence.reminder_definition_id,
                occurrence.scheduled_for.isoformat(),
            )
            if dedupe_key in existing_keys:
                continue
            saved_occurrence = (
                context.stores.reminders.save_reminder_occurrence(occurrence)
            )
            _sync_occurrence_projection(
                context=context,
                definition=definition,
                occurrence=saved_occurrence,
            )
            existing_keys.add(dedupe_key)
            created_events.append(
                _event_from_occurrence(definition, saved_occurrence)
            )

    signal_payload = {
        "user_id": user_profile.id,
        "reminder_count": len(created_events),
    }
    context.coordination_store.publish_signal(
        context.settings.storage.redis_worker_signal_channel, signal_payload
    )
    context.coordination_store.publish_signal(
        "reminders.ready", signal_payload
    )
    metrics = compute_mcr(
        context.stores.reminders.list_reminder_events(user_profile.id)
    )
    return created_events, metrics


def list_reminder_definitions_for_user(
    *, context: "AppContext", user_id: str
) -> list[ReminderDefinition]:
    return context.stores.reminders.list_reminder_definitions(
        user_id, active_only=True
    )


def create_reminder_definition_for_user(
    *,
    context: "AppContext",
    session: dict[str, object],
    definition: ReminderDefinition,
) -> ReminderDefinition:
    user_id = str(session["user_id"])
    definition.user_id = user_id
    saved = context.stores.reminders.save_reminder_definition(definition)
    if not saved.active:
        return saved

    user_profile: UserProfile = build_user_profile_from_session(
        session, context.stores.profiles
    )
    existing_keys = _existing_occurrence_keys(
        context=context, user_id=user_profile.id
    )
    target_date = datetime.now(timezone.utc).date()
    for occurrence in occurrences_for_definition(
        definition=saved, target_date=target_date, user_profile=user_profile
    ):
        dedupe_key = (
            occurrence.reminder_definition_id,
            occurrence.scheduled_for.isoformat(),
        )
        if dedupe_key in existing_keys:
            continue
        saved_occurrence = context.stores.reminders.save_reminder_occurrence(
            occurrence
        )
        _sync_occurrence_projection(
            context=context, definition=saved, occurrence=saved_occurrence
        )
        existing_keys.add(dedupe_key)
    return saved


def update_reminder_definition_for_user(
    *,
    context: "AppContext",
    user_id: str,
    session: dict[str, object] | None = None,
    reminder_definition_id: str,
    updates: dict[str, object],
) -> ReminderDefinition:
    existing = context.stores.reminders.get_reminder_definition(
        reminder_definition_id
    )
    if existing is None or existing.user_id != user_id:
        raise KeyError("reminder definition not found")
    schedule_changed = (
        "schedule" in updates and updates["schedule"] is not None
    )
    payload = existing.model_dump(mode="json")
    payload.update(
        {key: value for key, value in updates.items() if value is not None}
    )
    payload["updated_at"] = datetime.now(timezone.utc)
    updated = ReminderDefinition.model_validate(payload)
    saved = context.stores.reminders.save_reminder_definition(updated)

    if schedule_changed:
        now = datetime.now(timezone.utc)
        occurrences = context.stores.reminders.list_reminder_occurrences(
            user_id=user_id,
            reminder_definition_id=reminder_definition_id,
            limit=200,
        )
        for occurrence in occurrences:
            if occurrence.status not in {"scheduled", "queued", "processing"}:
                continue
            scheduled_notifications = (
                context.stores.reminders.list_scheduled_notifications(
                    reminder_id=occurrence.id,
                    user_id=user_id,
                )
            )
            cancel_reminder_notifications(
                repository=context.stores.reminders, reminder_id=occurrence.id
            )
            for scheduled in scheduled_notifications:
                context.app_store.mark_alert_dead_letter(
                    scheduled.id,
                    scheduled.channel,
                    error="cancelled_by_schedule_update",
                    attempt_count=scheduled.attempt_count,
                )
                context.stores.reminders.append_notification_log(
                    ReminderNotificationLogEntry(
                        id=str(uuid4()),
                        scheduled_notification_id=scheduled.id,
                        reminder_id=scheduled.reminder_id,
                        user_id=scheduled.user_id,
                        channel=scheduled.channel,
                        attempt_number=scheduled.attempt_count,
                        event_type="cancelled",
                        error_message="cancelled_by_schedule_update",
                    )
                )
            cancelled = occurrence.model_copy(
                update={
                    "status": "cancelled",
                    "action": "expired",
                    "action_outcome": "missed",
                    "acted_at": now,
                    "updated_at": now,
                }
            )
            context.stores.reminders.save_reminder_occurrence(cancelled)
            context.stores.reminders.save_reminder_event(
                _event_from_occurrence(saved, cancelled)
            )

        _ensure_today_occurrences_for_session(
            context=context,
            session=session or {"user_id": user_id, "account_role": "member"},
        )

    return saved


def _ensure_today_occurrences_for_session(
    *, context: "AppContext", session: dict[str, object]
) -> None:
    user_profile: UserProfile = build_user_profile_from_session(
        session, context.stores.profiles
    )
    definitions = context.stores.reminders.list_reminder_definitions(
        user_profile.id, active_only=True
    )
    existing_keys = _existing_occurrence_keys(
        context=context, user_id=user_profile.id
    )
    target_date = datetime.now(timezone.utc).date()
    for definition in definitions:
        for occurrence in occurrences_for_definition(
            definition=definition,
            target_date=target_date,
            user_profile=user_profile,
        ):
            dedupe_key = (
                occurrence.reminder_definition_id,
                occurrence.scheduled_for.isoformat(),
            )
            if dedupe_key in existing_keys:
                continue
            saved_occurrence = (
                context.stores.reminders.save_reminder_occurrence(occurrence)
            )
            _sync_occurrence_projection(
                context=context,
                definition=definition,
                occurrence=saved_occurrence,
            )
            existing_keys.add(dedupe_key)


def list_upcoming_occurrences_for_user(
    *,
    context: "AppContext",
    session: dict[str, object],
    user_id: str,
) -> list[ReminderOccurrence]:
    _ensure_today_occurrences_for_session(context=context, session=session)
    items = context.stores.reminders.list_reminder_occurrences(
        user_id=user_id, limit=200
    )
    return [
        item
        for item in items
        if item.status in {"scheduled", "queued", "processing"}
    ]


def list_history_occurrences_for_user(
    *, context: "AppContext", user_id: str
) -> list[ReminderOccurrence]:
    items = context.stores.reminders.list_reminder_occurrences(
        user_id=user_id, limit=200
    )
    return [
        item
        for item in items
        if item.status not in {"scheduled", "queued", "processing"}
    ]


def apply_occurrence_action_for_session(
    *,
    context: "AppContext",
    user_id: str,
    occurrence_id: str,
    action: str,
    snooze_minutes: int | None = None,
) -> ReminderOccurrence:
    occurrence = context.stores.reminders.get_reminder_occurrence(
        occurrence_id
    )
    if occurrence is None or occurrence.user_id != user_id:
        raise KeyError("reminder occurrence not found")
    definition = context.stores.reminders.get_reminder_definition(
        occurrence.reminder_definition_id
    )
    if definition is None:
        raise KeyError("reminder definition not found")

    acted_at = datetime.now(timezone.utc)
    context.stores.reminders.append_reminder_action(
        ReminderActionRecord(
            id=str(uuid4()),
            occurrence_id=occurrence.id,
            reminder_definition_id=definition.id,
            user_id=user_id,
            action=action,  # type: ignore[arg-type]
            acted_at=acted_at,
            snooze_minutes=snooze_minutes,
        )
    )

    if action == "snooze":
        delay = timedelta(minutes=snooze_minutes or 10)
        updated = context.stores.reminders.update_reminder_occurrence_status(
            occurrence_id=occurrence.id,
            status="scheduled",
            acted_at=acted_at,
            action="snooze",
            action_outcome="info",
            trigger_at=occurrence.trigger_at + delay,
        )
    else:
        status = "completed" if action == "taken" else "skipped"
        updated = context.stores.reminders.update_reminder_occurrence_status(
            occurrence_id=occurrence.id,
            status=status,
            acted_at=acted_at,
            action=action,
            action_outcome=(
                "on_time"
                if acted_at
                <= (
                    occurrence.scheduled_for
                    + timedelta(minutes=occurrence.grace_window_minutes)
                )
                else "late"
            ),
        )
        cancel_reminder_notifications(
            repository=context.stores.reminders, reminder_id=occurrence.id
        )
        event = context.stores.reminders.get_reminder_event(occurrence.id)
        if event is not None:
            event.status = "acknowledged" if action == "taken" else "missed"
            event.meal_confirmation = "yes" if action == "taken" else "no"
            event.ack_at = acted_at
            context.stores.reminders.save_reminder_event(event)
        if definition.regimen_id:
            context.stores.medications.save_medication_adherence_event(
                MedicationAdherenceEvent(
                    id=str(uuid4()),
                    user_id=user_id,
                    regimen_id=definition.regimen_id,
                    reminder_id=occurrence.id,
                    status="taken" if action == "taken" else "skipped",
                    scheduled_at=occurrence.scheduled_for,
                    taken_at=acted_at if action == "taken" else None,
                    source="reminder_confirm",
                    metadata={
                        "reminder_definition_id": definition.id,
                        "action": action,
                    },
                )
            )
    if updated is None:
        raise KeyError("failed to update reminder occurrence")
    return updated
