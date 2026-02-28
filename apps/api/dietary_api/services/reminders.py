from __future__ import annotations

from datetime import date, datetime, timezone

from apps.api.dietary_api.auth import build_user_profile_from_session
from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.routes_shared import default_demo_regimens
from apps.api.dietary_api.schemas import (
    ReminderConfirmResponse,
    ReminderGenerateResponse,
    ReminderListResponse,
)
from dietary_guardian.services.medication_service import (
    compute_mcr,
    generate_daily_reminders,
    mark_meal_confirmation,
)
from dietary_guardian.services.reminder_notification_service import (
    cancel_reminder_notifications,
    materialize_reminder_notifications,
)


def generate_reminders_for_session(*, context: AppContext, session: dict[str, object]) -> ReminderGenerateResponse:
    user_profile = build_user_profile_from_session(session, context.repository)
    reminders = generate_daily_reminders(
        user_profile,
        default_demo_regimens(user_profile.id),
        date.today(),
    )
    for reminder in reminders:
        context.repository.save_reminder_event(reminder)
        materialize_reminder_notifications(
            repository=context.repository,
            reminder_event=reminder,
            reminder_type="medication",
        )
    current_events = context.repository.list_reminder_events(user_profile.id)
    metrics = compute_mcr(current_events)
    return ReminderGenerateResponse(
        reminders=[item.model_dump(mode="json") for item in reminders],
        metrics=metrics.model_dump(mode="json"),
    )


def list_reminders_for_session(*, context: AppContext, user_id: str) -> ReminderListResponse:
    events = context.repository.list_reminder_events(user_id)
    metrics = compute_mcr(events)
    return ReminderListResponse(
        reminders=[item.model_dump(mode="json") for item in events],
        metrics=metrics.model_dump(mode="json"),
    )


def confirm_reminder_for_session(
    *,
    context: AppContext,
    user_id: str,
    event_id: str,
    confirmed: bool,
) -> ReminderConfirmResponse:
    event = context.repository.get_reminder_event(event_id)
    if event is None or event.user_id != user_id:
        raise build_api_error(status_code=404, code="reminders.not_found", message="reminder not found")
    updated = mark_meal_confirmation(
        event_id,
        confirmed,
        datetime.now(timezone.utc),
        context.repository,
    )
    cancel_reminder_notifications(repository=context.repository, reminder_id=event_id)
    metrics = compute_mcr(context.repository.list_reminder_events(user_id))
    return ReminderConfirmResponse(
        event=updated.model_dump(mode="json"),
        metrics=metrics.model_dump(mode="json"),
    )
