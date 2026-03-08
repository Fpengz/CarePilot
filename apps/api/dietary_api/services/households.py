from __future__ import annotations

from datetime import datetime
from typing import Literal, cast

from dietary_guardian.application.household import (
    HouseholdAlreadyExistsError,
    HouseholdForbiddenError,
    HouseholdInviteInvalidError,
    HouseholdMembershipConflictError,
    HouseholdNotFoundError,
    HouseholdOwnerLeaveForbiddenError,
    create_household_for_user,
    create_household_invite_for_owner,
    get_current_household_bundle,
    join_household_by_code,
    leave_household_for_member,
    list_household_members_for_user,
    rename_household_for_owner,
    remove_household_member_for_owner,
    validate_active_household_for_user,
)
from dietary_guardian.application.policies.household_access import (
    HouseholdAccessNotFoundError,
    ensure_household_member,
)
from dietary_guardian.services.health_profile_service import compute_profile_completeness
from dietary_guardian.services.health_profile_service import get_or_create_health_profile

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    HouseholdActiveUpdateResponse,
    HouseholdBundleResponse,
    HouseholdCareContextResponse,
    HouseholdCareMealSummaryResponse,
    HouseholdCareMembersResponse,
    HouseholdCareProfileResponse,
    HouseholdCareReminderListResponse,
    HouseholdInviteCreateResponse,
    HouseholdInviteResponseItem,
    HouseholdMemberItem,
    HouseholdMemberRemoveResponse,
    HouseholdMembersResponse,
    HouseholdResponse,
    HouseholdLeaveResponse,
)
from apps.api.dietary_api.services.health_profiles import _to_profile_response
from apps.api.dietary_api.services.meals import get_daily_summary
from apps.api.dietary_api.services.reminders import list_reminders_for_session


def _household_response(item: dict[str, object]) -> HouseholdResponse:
    return HouseholdResponse(
        household_id=str(item["household_id"]),
        name=str(item["name"]),
        owner_user_id=str(item["owner_user_id"]),
        created_at=datetime.fromisoformat(str(item["created_at"])),
    )


def _member_response(item: dict[str, object]) -> HouseholdMemberItem:
    return HouseholdMemberItem(
        user_id=str(item["user_id"]),
        display_name=str(item["display_name"]),
        role=cast(Literal["owner", "member"], item["role"]),
        joined_at=datetime.fromisoformat(str(item["joined_at"])),
    )


def _bundle_response(
    bundle_household: dict[str, object] | None,
    members: list[dict[str, object]],
    *,
    active_household_id: str | None = None,
) -> HouseholdBundleResponse:
    return HouseholdBundleResponse(
        household=(_household_response(bundle_household) if bundle_household is not None else None),
        members=[_member_response(item) for item in members],
        active_household_id=active_household_id,
    )


def _map_household_error(
    exc: Exception,
    *,
    not_found_message: str = "household not found",
) -> None:
    if isinstance(exc, HouseholdAlreadyExistsError | HouseholdMembershipConflictError):
        raise build_api_error(
            status_code=409,
            code="households.membership_conflict",
            message="user already belongs to a household",
        ) from exc
    if isinstance(exc, HouseholdInviteInvalidError):
        raise build_api_error(
            status_code=400,
            code="households.invalid_invite",
            message="invalid household invite",
        ) from exc
    if isinstance(exc, HouseholdOwnerLeaveForbiddenError):
        raise build_api_error(
            status_code=403,
            code="households.owner_leave_forbidden",
            message="household owner cannot leave",
        ) from exc
    if isinstance(exc, HouseholdForbiddenError):
        raise build_api_error(
            status_code=403,
            code="households.forbidden",
            message="forbidden",
        ) from exc
    if isinstance(exc, HouseholdNotFoundError):
        raise build_api_error(
            status_code=404,
            code="households.not_found",
            message=not_found_message,
        ) from exc
    raise exc


def create_household(
    *,
    context: AppContext,
    user_id: str,
    display_name: str,
    name: str,
) -> HouseholdBundleResponse:
    normalized = name.strip()
    if not normalized:
        raise build_api_error(
            status_code=400,
            code="households.invalid_name",
            message="household name must not be blank",
        )
    try:
        bundle = create_household_for_user(
            household_store=context.household_store,
            user_id=user_id,
            display_name=display_name,
            name=normalized,
        )
    except Exception as exc:
        _map_household_error(exc)
        raise
    return _bundle_response(bundle.household, bundle.members)


def get_current_household(
    *,
    context: AppContext,
    user_id: str,
    active_household_id: str | None,
) -> HouseholdBundleResponse:
    bundle = get_current_household_bundle(household_store=context.household_store, user_id=user_id)
    return _bundle_response(bundle.household, bundle.members, active_household_id=active_household_id)


def set_active_household(
    *,
    context: AppContext,
    session_id: str,
    user_id: str,
    household_id: str | None,
) -> HouseholdActiveUpdateResponse:
    try:
        active_household_id = validate_active_household_for_user(
            household_store=context.household_store,
            household_id=household_id,
            user_id=user_id,
        )
    except Exception as exc:
        _map_household_error(exc)
        raise
    updated = context.auth_store.set_active_household_for_session(
        session_id,
        active_household_id=active_household_id,
    )
    if updated is None:
        raise build_api_error(status_code=401, code="auth.invalid_session", message="invalid session")
    return HouseholdActiveUpdateResponse(active_household_id=active_household_id)


def list_household_members(
    *,
    context: AppContext,
    household_id: str,
    user_id: str,
) -> HouseholdMembersResponse:
    try:
        members = list_household_members_for_user(
            household_store=context.household_store,
            household_id=household_id,
            user_id=user_id,
        )
    except Exception as exc:
        _map_household_error(exc)
        raise
    return HouseholdMembersResponse(members=[_member_response(item) for item in members])


def rename_household(
    *,
    context: AppContext,
    household_id: str,
    actor_user_id: str,
    name: str,
    active_household_id: str | None,
) -> HouseholdBundleResponse:
    normalized = name.strip()
    if not normalized:
        raise build_api_error(
            status_code=400,
            code="households.invalid_name",
            message="household name must not be blank",
        )
    try:
        bundle = rename_household_for_owner(
            household_store=context.household_store,
            household_id=household_id,
            actor_user_id=actor_user_id,
            name=normalized,
        )
    except Exception as exc:
        _map_household_error(exc)
        raise
    return _bundle_response(bundle.household, bundle.members, active_household_id=active_household_id)


def create_household_invite(
    *,
    context: AppContext,
    household_id: str,
    user_id: str,
) -> HouseholdInviteCreateResponse:
    try:
        invite = create_household_invite_for_owner(
            household_store=context.household_store,
            household_id=household_id,
            user_id=user_id,
        )
    except Exception as exc:
        _map_household_error(exc)
        raise
    return HouseholdInviteCreateResponse(
        invite=HouseholdInviteResponseItem(
            invite_id=str(invite["invite_id"]),
            household_id=str(invite["household_id"]),
            code=str(invite["code"]),
            created_by_user_id=str(invite["created_by_user_id"]),
            created_at=datetime.fromisoformat(str(invite["created_at"])),
            expires_at=datetime.fromisoformat(str(invite["expires_at"])),
            max_uses=int(invite["max_uses"]),
            uses=int(invite["uses"]),
        )
    )


def join_household(
    *,
    context: AppContext,
    code: str,
    user_id: str,
    display_name: str,
) -> HouseholdBundleResponse:
    try:
        bundle = join_household_by_code(
            household_store=context.household_store,
            code=code.strip(),
            user_id=user_id,
            display_name=display_name,
        )
    except Exception as exc:
        _map_household_error(exc)
        raise
    return _bundle_response(bundle.household, bundle.members)


def remove_household_member(
    *,
    context: AppContext,
    household_id: str,
    actor_user_id: str,
    target_user_id: str,
) -> HouseholdMemberRemoveResponse:
    try:
        remove_household_member_for_owner(
            household_store=context.household_store,
            household_id=household_id,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
        )
    except Exception as exc:
        _map_household_error(exc, not_found_message="household member not found")
        raise
    return HouseholdMemberRemoveResponse(removed_user_id=target_user_id)


def leave_household(
    *,
    context: AppContext,
    household_id: str,
    user_id: str,
) -> HouseholdLeaveResponse:
    try:
        leave_household_for_member(
            household_store=context.household_store,
            household_id=household_id,
            user_id=user_id,
        )
    except Exception as exc:
        _map_household_error(exc)
        raise
    return HouseholdLeaveResponse(left_household_id=household_id)


def _ensure_household_subject_access(
    *,
    context: AppContext,
    household_id: str,
    viewer_user_id: str,
    subject_user_id: str | None = None,
) -> None:
    try:
        ensure_household_member(
            context.household_store,
            household_id=household_id,
            user_id=viewer_user_id,
        )
        if subject_user_id is not None:
            ensure_household_member(
                context.household_store,
                household_id=household_id,
                user_id=subject_user_id,
            )
    except HouseholdAccessNotFoundError as exc:
        raise build_api_error(
            status_code=404,
            code="households.not_found",
            message="household member not found",
        ) from exc


def _care_context(*, household_id: str, viewer_user_id: str, subject_user_id: str) -> HouseholdCareContextResponse:
    return HouseholdCareContextResponse(
        viewer_user_id=viewer_user_id,
        subject_user_id=subject_user_id,
        household_id=household_id,
    )


def list_household_care_members(
    *,
    context: AppContext,
    household_id: str,
    viewer_user_id: str,
) -> HouseholdCareMembersResponse:
    _ensure_household_subject_access(
        context=context,
        household_id=household_id,
        viewer_user_id=viewer_user_id,
    )
    members = context.household_store.list_members(household_id)
    return HouseholdCareMembersResponse(
        viewer_user_id=viewer_user_id,
        household_id=household_id,
        members=[_member_response(item) for item in members],
    )


def get_household_care_member_profile(
    *,
    context: AppContext,
    household_id: str,
    viewer_user_id: str,
    subject_user_id: str,
) -> HouseholdCareProfileResponse:
    _ensure_household_subject_access(
        context=context,
        household_id=household_id,
        viewer_user_id=viewer_user_id,
        subject_user_id=subject_user_id,
    )
    profile = get_or_create_health_profile(context.stores.profiles, subject_user_id)
    completeness = compute_profile_completeness(profile)
    return HouseholdCareProfileResponse(
        context=_care_context(
            household_id=household_id,
            viewer_user_id=viewer_user_id,
            subject_user_id=subject_user_id,
        ),
        profile=_to_profile_response(profile=profile, fallback_mode=completeness.state != "ready"),
    )


def get_household_care_member_daily_summary(
    *,
    context: AppContext,
    household_id: str,
    viewer_user_id: str,
    subject_user_id: str,
    summary_date,
) -> HouseholdCareMealSummaryResponse:
    _ensure_household_subject_access(
        context=context,
        household_id=household_id,
        viewer_user_id=viewer_user_id,
        subject_user_id=subject_user_id,
    )
    summary = get_daily_summary(
        context=context,
        user_id=subject_user_id,
        summary_date=summary_date,
    )
    return HouseholdCareMealSummaryResponse(
        context=_care_context(
            household_id=household_id,
            viewer_user_id=viewer_user_id,
            subject_user_id=subject_user_id,
        ),
        summary=summary,
    )


def list_household_care_member_reminders(
    *,
    context: AppContext,
    household_id: str,
    viewer_user_id: str,
    subject_user_id: str,
) -> HouseholdCareReminderListResponse:
    _ensure_household_subject_access(
        context=context,
        household_id=household_id,
        viewer_user_id=viewer_user_id,
        subject_user_id=subject_user_id,
    )
    reminder_list = list_reminders_for_session(
        context=context,
        user_id=subject_user_id,
    )
    return HouseholdCareReminderListResponse(
        context=_care_context(
            household_id=household_id,
            viewer_user_id=viewer_user_id,
            subject_user_id=subject_user_id,
        ),
        reminders=reminder_list.reminders,
        metrics=reminder_list.metrics,
    )
