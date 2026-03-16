"""
Implement reminder notification use cases.

This module provides reminder generation, listing, confirmation, and mobility
setting workflows.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

from apps.api.carepilot_api.deps import AppContext
from apps.api.carepilot_api.errors import build_api_error
from care_pilot.core.contracts.api import (
    MobilityReminderSettingsEnvelopeResponse,
    MobilityReminderSettingsRequest,
    MobilityReminderSettingsResponse,
    ReminderConfirmResponse,
    ReminderGenerateResponse,
    ReminderListResponse,
)
from care_pilot.platform.auth.session_context import (
    build_user_profile_from_session,
)
from care_pilot.features.medications.domain import (
    compute_mcr,
    default_mobility_settings,
    generate_mobility_reminders,
    mark_meal_confirmation,
    parse_hhmm,
)
from care_pilot.features.reminders.domain.models import (
    MobilityReminderSettings,
)
from care_pilot.features.companion.core.health.analytics import (
    EngagementMetrics,
)
from care_pilot.features.companion.core.health.models import (
    MedicationAdherenceEvent,
)
from care_pilot.features.reminders.notifications.reminder_materialization import (
    cancel_reminder_notifications,
    materialize_reminder_notifications,
)
from care_pilot.features.reminders.use_cases.structured import (
    apply_occurrence_action_for_session,
    generate_structured_reminders_for_session,
)


def _sort_at(item) -> datetime:  # noqa: ANN001
    value = item.scheduled_at
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def generate_reminders_for_session(
    *, context: AppContext, session: dict[str, object]
) -> ReminderGenerateResponse:
    user_profile = build_user_profile_from_session(session, context.stores.profiles)
    generated_reminders, metrics = generate_structured_reminders_for_session(
        context=context, session=session
    )
    mobility_settings = context.stores.reminders.get_mobility_reminder_settings(
        user_profile.id
    ) or default_mobility_settings(user_profile.id)
    mobility_reminders = generate_mobility_reminders(
        user_id=user_profile.id,
        target_date=date.today(),
        settings=mobility_settings,
    )
    for reminder in mobility_reminders:
        context.stores.reminders.save_reminder_event(reminder)
        materialize_reminder_notifications(
            repository=context.stores.reminders,
            reminder_event=reminder,
            reminder_type=reminder.reminder_type,
        )
    reminders = sorted(
        context.stores.reminders.list_reminder_events(user_profile.id),
        key=_sort_at,
    )
    return ReminderGenerateResponse(
        reminders=reminders,
        metrics=(metrics if isinstance(metrics, EngagementMetrics) else compute_mcr(reminders)),
    )


def list_reminders_for_session(*, context: AppContext, user_id: str) -> ReminderListResponse:
    events = context.stores.reminders.list_reminder_events(user_id)
    metrics = compute_mcr(events)
    return ReminderListResponse(
        reminders=events,
        metrics=metrics,
    )


def confirm_reminder_for_session(
    *,
    context: AppContext,
    user_id: str,
    event_id: str,
    confirmed: bool,
) -> ReminderConfirmResponse:
    event = context.stores.reminders.get_reminder_event(event_id)
    if event is None or event.user_id != user_id:
        raise build_api_error(
            status_code=404,
            code="reminders.not_found",
            message="reminder not found",
        )
    if event.occurrence_id:
        try:
            updated_occurrence = apply_occurrence_action_for_session(
                context=context,
                user_id=user_id,
                occurrence_id=event.occurrence_id,
                action="taken" if confirmed else "skipped",
            )
        except KeyError as exc:
            raise build_api_error(
                status_code=404,
                code="reminders.not_found",
                message="reminder not found",
            ) from exc
        updated_event = context.stores.reminders.get_reminder_event(updated_occurrence.id)
        metrics = compute_mcr(context.stores.reminders.list_reminder_events(user_id))
        return ReminderConfirmResponse(
            event=updated_event or event,
            metrics=metrics,
        )
    if event.reminder_type != "medication":
        raise build_api_error(
            status_code=400,
            code="reminders.unsupported_confirmation",
            message="only medication reminders support confirmation",
        )
    updated = mark_meal_confirmation(
        event_id,
        confirmed,
        datetime.now(timezone.utc),
        context.stores.reminders,
    )
    if updated.regimen_id is not None:
        adherence = MedicationAdherenceEvent(
            id=str(uuid4()),
            user_id=user_id,
            regimen_id=updated.regimen_id,
            reminder_id=updated.id,
            status="taken" if confirmed else "skipped",
            scheduled_at=updated.scheduled_at,
            taken_at=updated.ack_at if confirmed else None,
            source="reminder_confirm",
            metadata={"meal_confirmation": updated.meal_confirmation},
        )
        context.stores.medications.save_medication_adherence_event(adherence)
    cancel_reminder_notifications(repository=context.stores.reminders, reminder_id=event_id)
    metrics = compute_mcr(context.stores.reminders.list_reminder_events(user_id))
    return ReminderConfirmResponse(
        event=updated,
        metrics=metrics,
    )


def get_mobility_settings_for_session(
    *,
    context: AppContext,
    user_id: str,
) -> MobilityReminderSettingsEnvelopeResponse:
    settings = context.stores.reminders.get_mobility_reminder_settings(
        user_id
    ) or default_mobility_settings(user_id)
    return MobilityReminderSettingsEnvelopeResponse(
        settings=MobilityReminderSettingsResponse.model_validate(settings.model_dump(mode="json"))
    )


def update_mobility_settings_for_session(
    *,
    context: AppContext,
    user_id: str,
    payload: MobilityReminderSettingsRequest,
) -> MobilityReminderSettingsEnvelopeResponse:
    try:
        start = parse_hhmm(payload.active_start_time)
        end = parse_hhmm(payload.active_end_time)
    except ValueError as exc:
        raise build_api_error(
            status_code=400,
            code="reminders.invalid_time_window",
            message="invalid mobility reminder time window",
        ) from exc
    if start >= end:
        raise build_api_error(
            status_code=400,
            code="reminders.invalid_time_window",
            message="invalid mobility reminder time window",
        )
    settings = MobilityReminderSettings(
        user_id=user_id,
        enabled=payload.enabled,
        interval_minutes=payload.interval_minutes,
        active_start_time=payload.active_start_time,
        active_end_time=payload.active_end_time,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    context.stores.reminders.save_mobility_reminder_settings(settings)
    return MobilityReminderSettingsEnvelopeResponse(
        settings=MobilityReminderSettingsResponse.model_validate(settings.model_dump(mode="json"))
    )
