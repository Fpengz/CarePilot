from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from ..routes_shared import current_session, get_context
from ..schemas.households import (
    HouseholdActiveUpdateRequest,
    HouseholdActiveUpdateResponse,
    HouseholdBundleResponse,
    HouseholdCareMealSummaryResponse,
    HouseholdCareMembersResponse,
    HouseholdCareProfileResponse,
    HouseholdCareReminderListResponse,
    HouseholdCreateRequest,
    HouseholdInviteCreateResponse,
    HouseholdJoinRequest,
    HouseholdLeaveResponse,
    HouseholdMemberRemoveResponse,
    HouseholdMembersResponse,
    HouseholdUpdateRequest,
)
from ..services.households import (
    create_household,
    create_household_invite,
    get_current_household,
    get_household_care_member_daily_summary,
    get_household_care_member_profile,
    join_household,
    leave_household,
    list_household_care_member_reminders,
    list_household_care_members,
    list_household_members,
    remove_household_member,
    rename_household,
    set_active_household,
)
from ..routes_shared import require_action

router = APIRouter(tags=["households"])


@router.post("/api/v1/households", response_model=HouseholdBundleResponse)
def create_household_route(
    payload: HouseholdCreateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdBundleResponse:
    return create_household(
        context=get_context(request),
        user_id=str(session["user_id"]),
        display_name=str(session["display_name"]),
        name=payload.name,
    )


@router.get("/api/v1/households/current", response_model=HouseholdBundleResponse)
def get_current_household_route(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdBundleResponse:
    active_household_id = session.get("active_household_id")
    return get_current_household(
        context=get_context(request),
        user_id=str(session["user_id"]),
        active_household_id=(str(active_household_id) if isinstance(active_household_id, str) else None),
    )


@router.patch("/api/v1/households/active", response_model=HouseholdActiveUpdateResponse)
def set_active_household_route(
    payload: HouseholdActiveUpdateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdActiveUpdateResponse:
    return set_active_household(
        context=get_context(request),
        session_id=str(session["session_id"]),
        user_id=str(session["user_id"]),
        household_id=payload.household_id,
    )


@router.get("/api/v1/households/{household_id}/members", response_model=HouseholdMembersResponse)
def list_household_members_route(
    household_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdMembersResponse:
    return list_household_members(
        context=get_context(request),
        household_id=household_id,
        user_id=str(session["user_id"]),
    )


@router.get("/api/v1/households/{household_id}/care/members", response_model=HouseholdCareMembersResponse)
def list_household_care_members_route(
    household_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdCareMembersResponse:
    require_action(session, "households.care.read_members")
    return list_household_care_members(
        context=get_context(request),
        household_id=household_id,
        viewer_user_id=str(session["user_id"]),
    )


@router.get(
    "/api/v1/households/{household_id}/care/members/{member_user_id}/profile",
    response_model=HouseholdCareProfileResponse,
)
def get_household_care_member_profile_route(
    household_id: str,
    member_user_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdCareProfileResponse:
    require_action(session, "households.care.read_profile")
    return get_household_care_member_profile(
        context=get_context(request),
        household_id=household_id,
        viewer_user_id=str(session["user_id"]),
        subject_user_id=member_user_id,
    )


@router.get(
    "/api/v1/households/{household_id}/care/members/{member_user_id}/meal-daily-summary",
    response_model=HouseholdCareMealSummaryResponse,
)
def get_household_care_member_daily_summary_route(
    household_id: str,
    member_user_id: str,
    request: Request,
    summary_date: date = Query(alias="date"),
    session: dict[str, object] = Depends(current_session),
) -> HouseholdCareMealSummaryResponse:
    require_action(session, "households.care.read_meals")
    return get_household_care_member_daily_summary(
        context=get_context(request),
        household_id=household_id,
        viewer_user_id=str(session["user_id"]),
        subject_user_id=member_user_id,
        summary_date=summary_date,
    )


@router.get(
    "/api/v1/households/{household_id}/care/members/{member_user_id}/reminders",
    response_model=HouseholdCareReminderListResponse,
)
def list_household_care_member_reminders_route(
    household_id: str,
    member_user_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdCareReminderListResponse:
    require_action(session, "households.care.read_reminders")
    return list_household_care_member_reminders(
        context=get_context(request),
        household_id=household_id,
        viewer_user_id=str(session["user_id"]),
        subject_user_id=member_user_id,
    )


@router.patch("/api/v1/households/{household_id}", response_model=HouseholdBundleResponse)
def rename_household_route(
    household_id: str,
    payload: HouseholdUpdateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdBundleResponse:
    active_household_id = session.get("active_household_id")
    return rename_household(
        context=get_context(request),
        household_id=household_id,
        actor_user_id=str(session["user_id"]),
        name=payload.name,
        active_household_id=(str(active_household_id) if isinstance(active_household_id, str) else None),
    )


@router.post("/api/v1/households/{household_id}/invites", response_model=HouseholdInviteCreateResponse)
def create_household_invite_route(
    household_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdInviteCreateResponse:
    return create_household_invite(
        context=get_context(request),
        household_id=household_id,
        user_id=str(session["user_id"]),
    )


@router.post("/api/v1/households/join", response_model=HouseholdBundleResponse)
def join_household_route(
    payload: HouseholdJoinRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdBundleResponse:
    return join_household(
        context=get_context(request),
        code=payload.code,
        user_id=str(session["user_id"]),
        display_name=str(session["display_name"]),
    )


@router.post("/api/v1/households/{household_id}/members/{user_id}/remove", response_model=HouseholdMemberRemoveResponse)
def remove_household_member_route(
    household_id: str,
    user_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdMemberRemoveResponse:
    return remove_household_member(
        context=get_context(request),
        household_id=household_id,
        actor_user_id=str(session["user_id"]),
        target_user_id=user_id,
    )


@router.post("/api/v1/households/{household_id}/leave", response_model=HouseholdLeaveResponse)
def leave_household_route(
    household_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdLeaveResponse:
    return leave_household(
        context=get_context(request),
        household_id=household_id,
        user_id=str(session["user_id"]),
    )
