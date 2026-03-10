"""Lifecycle operations for household membership and invite management."""

from __future__ import annotations

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    HouseholdActiveUpdateResponse,
    HouseholdBundleResponse,
    HouseholdInviteCreateResponse,
    HouseholdLeaveResponse,
    HouseholdMemberRemoveResponse,
    HouseholdMembersResponse,
)
from apps.api.dietary_api.services.households_support import (
    household_bundle_response,
    household_invite_response,
    household_member_response,
    map_household_error,
)
from dietary_guardian.application.household import (
    create_household_for_user,
    create_household_invite_for_owner,
    get_current_household_bundle,
    join_household_by_code,
    leave_household_for_member,
    list_household_members_for_user,
    remove_household_member_for_owner,
    rename_household_for_owner,
    validate_active_household_for_user,
)


def create_household(
    *,
    context: AppContext,
    user_id: str,
    display_name: str,
    name: str,
) -> HouseholdBundleResponse:
    """Create a household owned by the current user."""
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
        map_household_error(exc)
        raise
    return household_bundle_response(bundle.household, bundle.members)



def get_current_household(
    *,
    context: AppContext,
    user_id: str,
    active_household_id: str | None,
) -> HouseholdBundleResponse:
    """Fetch the caller's current household and member roster."""
    bundle = get_current_household_bundle(household_store=context.household_store, user_id=user_id)
    return household_bundle_response(bundle.household, bundle.members, active_household_id=active_household_id)



def set_active_household(
    *,
    context: AppContext,
    session_id: str,
    user_id: str,
    household_id: str | None,
) -> HouseholdActiveUpdateResponse:
    """Persist the active household selection on the caller session."""
    try:
        active_household_id = validate_active_household_for_user(
            household_store=context.household_store,
            household_id=household_id,
            user_id=user_id,
        )
    except Exception as exc:
        map_household_error(exc)
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
    """List members visible to the current household participant."""
    try:
        members = list_household_members_for_user(
            household_store=context.household_store,
            household_id=household_id,
            user_id=user_id,
        )
    except Exception as exc:
        map_household_error(exc)
        raise
    return HouseholdMembersResponse(members=[household_member_response(item) for item in members])



def rename_household(
    *,
    context: AppContext,
    household_id: str,
    actor_user_id: str,
    name: str,
    active_household_id: str | None,
) -> HouseholdBundleResponse:
    """Rename a household owned by the acting user."""
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
        map_household_error(exc)
        raise
    return household_bundle_response(bundle.household, bundle.members, active_household_id=active_household_id)



def create_household_invite(
    *,
    context: AppContext,
    household_id: str,
    user_id: str,
) -> HouseholdInviteCreateResponse:
    """Create a join code for an existing household."""
    try:
        invite = create_household_invite_for_owner(
            household_store=context.household_store,
            household_id=household_id,
            user_id=user_id,
        )
    except Exception as exc:
        map_household_error(exc)
        raise
    return HouseholdInviteCreateResponse(invite=household_invite_response(invite))



def join_household(
    *,
    context: AppContext,
    code: str,
    user_id: str,
    display_name: str,
) -> HouseholdBundleResponse:
    """Join a household using an invite code."""
    try:
        bundle = join_household_by_code(
            household_store=context.household_store,
            code=code.strip(),
            user_id=user_id,
            display_name=display_name,
        )
    except Exception as exc:
        map_household_error(exc)
        raise
    return household_bundle_response(bundle.household, bundle.members)



def remove_household_member(
    *,
    context: AppContext,
    household_id: str,
    actor_user_id: str,
    target_user_id: str,
) -> HouseholdMemberRemoveResponse:
    """Remove a member from a household on behalf of the owner."""
    try:
        remove_household_member_for_owner(
            household_store=context.household_store,
            household_id=household_id,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
        )
    except Exception as exc:
        map_household_error(exc, not_found_message="household member not found")
        raise
    return HouseholdMemberRemoveResponse(removed_user_id=target_user_id)



def leave_household(
    *,
    context: AppContext,
    household_id: str,
    user_id: str,
) -> HouseholdLeaveResponse:
    """Leave a household as the current member."""
    try:
        leave_household_for_member(
            household_store=context.household_store,
            household_id=household_id,
            user_id=user_id,
        )
    except Exception as exc:
        map_household_error(exc)
        raise
    return HouseholdLeaveResponse(left_household_id=household_id)


__all__ = [
    "create_household",
    "create_household_invite",
    "get_current_household",
    "join_household",
    "leave_household",
    "list_household_members",
    "remove_household_member",
    "rename_household",
    "set_active_household",
]
