"""
Expose reminder API endpoints.

This router defines reminder scheduling and confirmation routes and delegates
to reminder services for orchestration.
"""

from fastapi import APIRouter, Depends, Request

from ..routes_shared import current_session, get_context, require_action
from ..schemas import (
    ReminderDefinitionCreateRequest,
    ReminderDefinitionEnvelopeResponse,
    ReminderDefinitionListResponse,
    ReminderDefinitionPatchRequest,
    MobilityReminderSettingsEnvelopeResponse,
    ReminderOccurrenceActionRequest,
    ReminderOccurrenceActionResponse,
    ReminderOccurrenceListResponse,
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
from ..errors import build_api_error
from dietary_guardian.features.reminders.notifications.reminder_materialization import (
    list_notification_endpoints,
    list_notification_preferences,
    list_reminder_notification_logs,
    list_reminder_notification_schedules,
    replace_notification_endpoints,
    replace_notification_preferences,
)
from dietary_guardian.features.reminders.service import (
    confirm_reminder_for_session,
    generate_reminders_for_session,
    get_mobility_settings_for_session,
    list_reminders_for_session,
    update_mobility_settings_for_session,
)
from dietary_guardian.features.reminders.use_cases import (
    apply_occurrence_action_for_session,
    create_reminder_definition_for_user,
    list_history_occurrences_for_user,
    list_reminder_definitions_for_user,
    list_upcoming_occurrences_for_user,
    update_reminder_definition_for_user,
)
from dietary_guardian.features.reminders.domain.models import ReminderDefinition
from datetime import datetime, timezone
from uuid import uuid4

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


@router.get("/api/v1/reminders/definitions", response_model=ReminderDefinitionListResponse)
def reminder_definitions_list(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderDefinitionListResponse:
    require_action(session, "reminders.read")
    return ReminderDefinitionListResponse(
        items=list_reminder_definitions_for_user(
            context=get_context(request),
            user_id=str(session["user_id"]),
        )
    )


@router.post("/api/v1/reminders/definitions", response_model=ReminderDefinitionEnvelopeResponse)
def reminder_definitions_create(
    payload: ReminderDefinitionCreateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderDefinitionEnvelopeResponse:
    require_action(session, "reminders.confirm")
    item = create_reminder_definition_for_user(
        context=get_context(request),
        session=session,
        definition=ReminderDefinition(
            id=str(uuid4()),
            user_id=str(session["user_id"]),
            regimen_id=payload.regimen_id,
            reminder_type=payload.reminder_type,
            source=payload.source,
            title=payload.title,
            body=payload.body,
            medication_name=payload.medication_name,
            dosage_text=payload.dosage_text,
            route=payload.route,
            instructions_text=payload.instructions_text,
            special_notes=payload.special_notes,
            treatment_duration=payload.treatment_duration,
            channels=payload.channels,
            timezone=payload.timezone,
            schedule=payload.schedule,
            active=payload.active,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    )
    return ReminderDefinitionEnvelopeResponse(item=item)


@router.patch("/api/v1/reminders/definitions/{reminder_definition_id}", response_model=ReminderDefinitionEnvelopeResponse)
def reminder_definitions_patch(
    reminder_definition_id: str,
    payload: ReminderDefinitionPatchRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderDefinitionEnvelopeResponse:
    require_action(session, "reminders.confirm")
    try:
        item = update_reminder_definition_for_user(
            context=get_context(request),
            user_id=str(session["user_id"]),
            reminder_definition_id=reminder_definition_id,
            updates=payload.model_dump(exclude_unset=True),
        )
    except KeyError as exc:
        raise build_api_error(status_code=404, code="reminders.not_found", message="reminder not found") from exc
    return ReminderDefinitionEnvelopeResponse(item=item)


@router.get("/api/v1/reminders/upcoming", response_model=ReminderOccurrenceListResponse)
def reminder_occurrences_upcoming(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderOccurrenceListResponse:
    require_action(session, "reminders.read")
    return ReminderOccurrenceListResponse(
        items=list_upcoming_occurrences_for_user(
            context=get_context(request),
            user_id=str(session["user_id"]),
        )
    )


@router.get("/api/v1/reminders/history", response_model=ReminderOccurrenceListResponse)
def reminder_occurrences_history(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderOccurrenceListResponse:
    require_action(session, "reminders.read")
    return ReminderOccurrenceListResponse(
        items=list_history_occurrences_for_user(
            context=get_context(request),
            user_id=str(session["user_id"]),
        )
    )


@router.post("/api/v1/reminders/occurrences/{occurrence_id}/actions", response_model=ReminderOccurrenceActionResponse)
def reminder_occurrences_action(
    occurrence_id: str,
    payload: ReminderOccurrenceActionRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ReminderOccurrenceActionResponse:
    require_action(session, "reminders.confirm")
    try:
        occurrence = apply_occurrence_action_for_session(
            context=get_context(request),
            user_id=str(session["user_id"]),
            occurrence_id=occurrence_id,
            action=payload.action,
            snooze_minutes=payload.snooze_minutes,
        )
    except KeyError as exc:
        raise build_api_error(status_code=404, code="reminders.not_found", message="reminder not found") from exc
    return ReminderOccurrenceActionResponse(occurrence=occurrence)


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
