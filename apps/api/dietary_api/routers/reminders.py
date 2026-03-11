"""API router for reminders endpoints."""

from fastapi import APIRouter, Depends, Request

from ..routes_shared import current_session, get_context, require_action
from ..schemas import (
    MobilityReminderSettingsEnvelopeResponse,
    MobilityReminderSettingsRequest,
    ReminderConfirmRequest,
    ReminderConfirmResponse,
    ReminderGenerateResponse,
    ReminderListResponse,
    ReminderNotificationEndpointListResponse,
    ReminderNotificationEndpointUpdateRequest,
    ReminderNotificationLogListResponse,
    ReminderNotificationPreferenceListResponse,
    ReminderNotificationPreferenceUpdateRequest,
    ScheduledReminderNotificationListResponse,
)
from dietary_guardian.application.notifications.reminder_materialization import (
    list_notification_endpoints,
    list_notification_preferences,
    list_reminder_notification_logs,
    list_reminder_notification_schedules,
    replace_notification_endpoints,
    replace_notification_preferences,
)
from dietary_guardian.application.notifications.reminders import (
    confirm_reminder_for_session,
    generate_reminders_for_session,
    get_mobility_settings_for_session,
    list_reminders_for_session,
    update_mobility_settings_for_session,
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


@router.get("/api/v1/reminders/mobility-settings", response_model=MobilityReminderSettingsEnvelopeResponse)
def reminders_mobility_settings_get(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> MobilityReminderSettingsEnvelopeResponse:
    require_action(session, "reminders.read")
    return get_mobility_settings_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
    )


@router.put("/api/v1/reminders/mobility-settings", response_model=MobilityReminderSettingsEnvelopeResponse)
def reminders_mobility_settings_put(
    payload: MobilityReminderSettingsRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> MobilityReminderSettingsEnvelopeResponse:
    require_action(session, "reminders.confirm")
    return update_mobility_settings_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        payload=payload,
    )


@router.get("/api/v1/reminder-notification-preferences", response_model=ReminderNotificationPreferenceListResponse)
def reminder_notification_preferences_list(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderNotificationPreferenceListResponse:
    require_action(session, "reminders.read")
    return list_notification_preferences(
        context=get_context(request),
        user_id=str(session["user_id"]),
    )


@router.put("/api/v1/reminder-notification-preferences/default", response_model=ReminderNotificationPreferenceListResponse)
def reminder_notification_preferences_replace_default(
    payload: ReminderNotificationPreferenceUpdateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderNotificationPreferenceListResponse:
    require_action(session, "reminders.confirm")
    return replace_notification_preferences(
        context=get_context(request),
        user_id=str(session["user_id"]),
        scope_type="default",
        scope_key=None,
        rules=payload.rules,
    )


@router.put(
    "/api/v1/reminder-notification-preferences/reminder-types/{reminder_type}",
    response_model=ReminderNotificationPreferenceListResponse,
)
def reminder_notification_preferences_replace_by_type(
    reminder_type: str,
    payload: ReminderNotificationPreferenceUpdateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderNotificationPreferenceListResponse:
    require_action(session, "reminders.confirm")
    return replace_notification_preferences(
        context=get_context(request),
        user_id=str(session["user_id"]),
        scope_type="reminder_type",
        scope_key=reminder_type,
        rules=payload.rules,
    )


@router.get(
    "/api/v1/reminders/{event_id}/notification-schedules",
    response_model=ScheduledReminderNotificationListResponse,
)
def reminder_notification_schedules_list(
    event_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ScheduledReminderNotificationListResponse:
    require_action(session, "reminders.read")
    return list_reminder_notification_schedules(
        context=get_context(request),
        user_id=str(session["user_id"]),
        reminder_id=event_id,
    )


@router.get("/api/v1/reminder-notification-endpoints", response_model=ReminderNotificationEndpointListResponse)
def reminder_notification_endpoints_list(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderNotificationEndpointListResponse:
    require_action(session, "reminders.read")
    return list_notification_endpoints(
        context=get_context(request),
        user_id=str(session["user_id"]),
    )


@router.put("/api/v1/reminder-notification-endpoints", response_model=ReminderNotificationEndpointListResponse)
def reminder_notification_endpoints_replace(
    payload: ReminderNotificationEndpointUpdateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderNotificationEndpointListResponse:
    require_action(session, "reminders.confirm")
    return replace_notification_endpoints(
        context=get_context(request),
        user_id=str(session["user_id"]),
        endpoints=payload.endpoints,
    )


@router.get("/api/v1/reminders/{event_id}/notification-logs", response_model=ReminderNotificationLogListResponse)
def reminder_notification_logs_list(
    event_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderNotificationLogListResponse:
    require_action(session, "reminders.read")
    return list_reminder_notification_logs(
        context=get_context(request),
        user_id=str(session["user_id"]),
        reminder_id=event_id,
    )
