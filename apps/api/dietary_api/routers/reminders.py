from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from dietary_guardian.services.medication_service import (
    compute_mcr,
    generate_daily_reminders,
    mark_meal_confirmation,
)

from ..auth import build_user_profile_from_session
from ..routes_shared import current_session, default_demo_regimens, get_context, require_scopes
from ..schemas import (
    ReminderConfirmRequest,
    ReminderConfirmResponse,
    ReminderGenerateResponse,
    ReminderListResponse,
)

router = APIRouter(tags=["reminders"])


@router.post("/api/v1/reminders/generate", response_model=ReminderGenerateResponse)
def reminders_generate(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderGenerateResponse:
    require_scopes(session, {"reminder:write"})
    context = get_context(request)
    user_profile = build_user_profile_from_session(session)
    reminders = generate_daily_reminders(
        user_profile,
        default_demo_regimens(user_profile.id),
        date.today(),
    )
    for reminder in reminders:
        context.repository.save_reminder_event(reminder)
    current_events = context.repository.list_reminder_events(user_profile.id)
    metrics = compute_mcr(current_events)
    return ReminderGenerateResponse(
        reminders=[item.model_dump(mode="json") for item in reminders],
        metrics=metrics.model_dump(mode="json"),
    )


@router.get("/api/v1/reminders", response_model=ReminderListResponse)
def reminders_list(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderListResponse:
    require_scopes(session, {"reminder:read"})
    context = get_context(request)
    user_id = str(session["user_id"])
    events = context.repository.list_reminder_events(user_id)
    metrics = compute_mcr(events)
    return ReminderListResponse(
        reminders=[item.model_dump(mode="json") for item in events],
        metrics=metrics.model_dump(mode="json"),
    )


@router.post("/api/v1/reminders/{event_id}/confirm", response_model=ReminderConfirmResponse)
def reminders_confirm(
    event_id: str,
    payload: ReminderConfirmRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderConfirmResponse:
    require_scopes(session, {"reminder:write"})
    context = get_context(request)
    user_id = str(session["user_id"])
    event = context.repository.get_reminder_event(event_id)
    if event is None or event.user_id != user_id:
        raise HTTPException(status_code=404, detail="reminder not found")
    updated = mark_meal_confirmation(
        event_id,
        payload.confirmed,
        datetime.now(timezone.utc),
        context.repository,
    )
    metrics = compute_mcr(context.repository.list_reminder_events(user_id))
    return ReminderConfirmResponse(
        event=updated.model_dump(mode="json"),
        metrics=metrics.model_dump(mode="json"),
    )
