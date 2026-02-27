from fastapi import APIRouter, Depends, Request

from ..routes_shared import current_session, get_context, require_action
from ..schemas import (
    ReminderConfirmRequest,
    ReminderConfirmResponse,
    ReminderGenerateResponse,
    ReminderListResponse,
)
from ..services.reminders import (
    confirm_reminder_for_session,
    generate_reminders_for_session,
    list_reminders_for_session,
)

router = APIRouter(tags=["reminders"])


@router.post("/api/v1/reminders/generate", response_model=ReminderGenerateResponse)
def reminders_generate(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderGenerateResponse:
    require_action(session, "reminders.generate")
    return generate_reminders_for_session(context=get_context(request), session=session)


@router.get("/api/v1/reminders", response_model=ReminderListResponse)
def reminders_list(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderListResponse:
    require_action(session, "reminders.read")
    return list_reminders_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
    )


@router.post("/api/v1/reminders/{event_id}/confirm", response_model=ReminderConfirmResponse)
def reminders_confirm(
    event_id: str,
    payload: ReminderConfirmRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderConfirmResponse:
    require_action(session, "reminders.confirm")
    return confirm_reminder_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        event_id=event_id,
        confirmed=payload.confirmed,
    )
