"""API helpers for reminder generation, listing, confirmation, and mobility settings."""

from __future__ import annotations

from datetime import date, datetime, timezone

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.routes_shared import default_demo_regimens
from apps.api.dietary_api.schemas import (
    MobilityReminderSettingsEnvelopeResponse,
    MobilityReminderSettingsRequest,
    MobilityReminderSettingsResponse,
    ReminderConfirmResponse,
    ReminderGenerateResponse,
    ReminderListResponse,
)
from apps.api.dietary_api.session_profiles import build_user_profile_from_session
from dietary_guardian.domain.medications import (
    compute_mcr,
    default_mobility_settings,
    generate_daily_reminders,
    generate_mobility_reminders,
    mark_meal_confirmation,
    parse_hhmm,
)
from dietary_guardian.domain.notifications.models import MobilityReminderSettings
from dietary_guardian.application.notifications.reminder_materialization import (
    cancel_reminder_notifications,
    materialize_reminder_notifications,
)


def generate_reminders_for_session(*, context: AppContext, session: dict[str, object]) -> ReminderGenerateResponse:
    user_profile = build_user_profile_from_session(session, context.stores.profiles)
    regimens = context.stores.medications.list_medication_regimens(user_profile.id, active_only=True)
    if not regimens:
        regimens = default_demo_regimens(user_profile.id)
        for item in regimens:
            context.stores.medications.save_medication_regimen(item)
    reminders = generate_daily_reminders(
        user_profile,
        regimens,
        date.today(),
    )
    mobility_settings = context.stores.reminders.get_mobility_reminder_settings(user_profile.id) or default_mobility_settings(user_profile.id)
    reminders.extend(
        generate_mobility_reminders(
            user_id=user_profile.id,
            target_date=date.today(),
            settings=mobility_settings,
        )
    )
    reminders = sorted(reminders, key=lambda item: item.scheduled_at)
    for reminder in reminders:
        context.stores.reminders.save_reminder_event(reminder)
        materialize_reminder_notifications(
            repository=context.stores.reminders,
            reminder_event=reminder,
            reminder_type=reminder.reminder_type,
        )
    signal_payload = {"user_id": user_profile.id, "reminder_count": len(reminders)}
    context.coordination_store.publish_signal(context.settings.storage.redis_worker_signal_channel, signal_payload)
    context.coordination_store.publish_signal("reminders.ready", signal_payload)
    current_events = context.stores.reminders.list_reminder_events(user_profile.id)
    metrics = compute_mcr(current_events)
    return ReminderGenerateResponse(
        reminders=reminders,
        metrics=metrics,
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
        raise build_api_error(status_code=404, code="reminders.not_found", message="reminder not found")
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
    settings = context.stores.reminders.get_mobility_reminder_settings(user_id) or default_mobility_settings(user_id)
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
