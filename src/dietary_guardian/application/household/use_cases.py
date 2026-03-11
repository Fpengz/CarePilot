"""Application use cases for household.

Consolidates lifecycle operations, access checks, caregiver-facing aggregates,
and shared response/error helpers previously spread across five service modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, cast

from dietary_guardian.application.policies.household_access import (
    HouseholdAccessForbiddenError,
    HouseholdAccessNotFoundError,
    ensure_household_member,
    ensure_household_owner,
)
from dietary_guardian.domain.identity.health_profile import (
    compute_profile_completeness,
    get_or_create_health_profile,
)

from .ports import HouseholdStorePort

# ---------------------------------------------------------------------------
# Deferred imports: these pull in the API layer which depends on this module
# indirectly.  We import them here so that ruff can resolve the names used in
# return type annotations.  Python will resolve the actual objects at call time
# when all modules are already loaded.
# ---------------------------------------------------------------------------
from apps.api.dietary_api.deps import AppContext  # noqa: E402
from apps.api.dietary_api.errors import build_api_error  # noqa: E402
from apps.api.dietary_api.schemas import (  # noqa: E402
    HouseholdActiveUpdateResponse,
    HouseholdBundleResponse,
    HouseholdCareContextResponse,
    HouseholdCareMealSummaryResponse,
    HouseholdCareMembersResponse,
    HouseholdCareProfileResponse,
    HouseholdCareReminderListResponse,
    HouseholdInviteCreateResponse,
    HouseholdInviteResponseItem,
    HouseholdLeaveResponse,
    HouseholdMemberItem,
    HouseholdMemberRemoveResponse,
    HouseholdMembersResponse,
    HouseholdResponse,
)


class HouseholdAlreadyExistsError(Exception):
    pass


class HouseholdNotFoundError(Exception):
    pass


class HouseholdForbiddenError(Exception):
    pass


class HouseholdInviteInvalidError(Exception):
    pass


class HouseholdMembershipConflictError(Exception):
    pass


class HouseholdOwnerLeaveForbiddenError(Exception):
    pass


@dataclass
class HouseholdBundle:
    household: dict[str, Any] | None
    members: list[dict[str, Any]]


@dataclass
class HouseholdInviteResult:
    household: dict[str, Any]
    invite: dict[str, Any]


def get_current_household_bundle(*, household_store: HouseholdStorePort, user_id: str) -> HouseholdBundle:
    household = household_store.get_household_for_user(user_id)
    if household is None:
        return HouseholdBundle(household=None, members=[])
    return HouseholdBundle(household=household, members=household_store.list_members(str(household["household_id"])))


def create_household_for_user(
    *,
    household_store: HouseholdStorePort,
    user_id: str,
    display_name: str,
    name: str,
) -> HouseholdBundle:
    if household_store.get_household_for_user(user_id) is not None:
        raise HouseholdAlreadyExistsError
    household = household_store.create_household(
        owner_user_id=user_id,
        owner_display_name=display_name,
        name=name,
    )
    return HouseholdBundle(household=household, members=household_store.list_members(str(household["household_id"])))


def list_household_members_for_user(
    *, household_store: HouseholdStorePort, household_id: str, user_id: str
) -> list[dict[str, Any]]:
    try:
        ensure_household_member(household_store, household_id=household_id, user_id=user_id)
    except HouseholdAccessNotFoundError:
        raise HouseholdNotFoundError
    return household_store.list_members(household_id)


def create_household_invite_for_owner(
    *, household_store: HouseholdStorePort, household_id: str, user_id: str
) -> dict[str, Any]:
    try:
        ensure_household_owner(household_store, household_id=household_id, user_id=user_id)
    except HouseholdAccessNotFoundError:
        raise HouseholdNotFoundError
    except HouseholdAccessForbiddenError:
        raise HouseholdForbiddenError
    return household_store.create_invite(household_id=household_id, created_by_user_id=user_id)


def join_household_by_code(
    *,
    household_store: HouseholdStorePort,
    code: str,
    user_id: str,
    display_name: str,
) -> HouseholdBundle:
    if household_store.get_household_for_user(user_id) is not None:
        raise HouseholdMembershipConflictError
    result = household_store.join_by_invite(code=code, user_id=user_id, display_name=display_name)
    if result is None:
        raise HouseholdInviteInvalidError
    household, joined = result
    if not joined:
        raise HouseholdMembershipConflictError
    return HouseholdBundle(household=household, members=household_store.list_members(str(household["household_id"])))


def remove_household_member_for_owner(
    *, household_store: HouseholdStorePort, household_id: str, actor_user_id: str, target_user_id: str
) -> None:
    try:
        ensure_household_owner(household_store, household_id=household_id, user_id=actor_user_id)
    except HouseholdAccessNotFoundError:
        raise HouseholdNotFoundError
    except HouseholdAccessForbiddenError:
        raise HouseholdForbiddenError
    try:
        target_role = ensure_household_member(
            household_store, household_id=household_id, user_id=target_user_id
        )
    except HouseholdAccessNotFoundError:
        raise HouseholdNotFoundError
    if target_role == "owner":
        raise HouseholdForbiddenError
    removed = household_store.remove_member(household_id=household_id, user_id=target_user_id)
    if not removed:
        raise HouseholdNotFoundError


def leave_household_for_member(*, household_store: HouseholdStorePort, household_id: str, user_id: str) -> None:
    try:
        role = ensure_household_member(household_store, household_id=household_id, user_id=user_id)
    except HouseholdAccessNotFoundError:
        raise HouseholdNotFoundError
    if role == "owner":
        raise HouseholdOwnerLeaveForbiddenError
    removed = household_store.remove_member(household_id=household_id, user_id=user_id)
    if not removed:
        raise HouseholdNotFoundError


def rename_household_for_owner(
    *, household_store: HouseholdStorePort, household_id: str, actor_user_id: str, name: str
) -> HouseholdBundle:
    try:
        ensure_household_owner(household_store, household_id=household_id, user_id=actor_user_id)
    except HouseholdAccessNotFoundError:
        raise HouseholdNotFoundError
    except HouseholdAccessForbiddenError:
        raise HouseholdForbiddenError
    household = household_store.rename_household(household_id=household_id, name=name)
    if household is None:
        raise HouseholdNotFoundError
    return HouseholdBundle(household=household, members=household_store.list_members(household_id))


def validate_active_household_for_user(
    *, household_store: HouseholdStorePort, household_id: str | None, user_id: str
) -> str | None:
    if household_id is None:
        return None
    try:
        ensure_household_member(household_store, household_id=household_id, user_id=user_id)
    except HouseholdAccessNotFoundError:
        raise HouseholdNotFoundError
    return household_id


# ---------------------------------------------------------------------------
# Support helpers (response projectors + error mapping)
# ---------------------------------------------------------------------------

def household_response(item: dict[str, object]) -> HouseholdResponse:
    """Convert a persisted household record into the API response model."""
    return HouseholdResponse(
        household_id=str(item["household_id"]),
        name=str(item["name"]),
        owner_user_id=str(item["owner_user_id"]),
        created_at=datetime.fromisoformat(str(item["created_at"])),
    )


def household_member_response(item: dict[str, object]) -> HouseholdMemberItem:
    """Convert a persisted household member record into the API response model."""
    return HouseholdMemberItem(
        user_id=str(item["user_id"]),
        display_name=str(item["display_name"]),
        role=cast(Literal["owner", "member"], item["role"]),
        joined_at=datetime.fromisoformat(str(item["joined_at"])),
    )


def household_bundle_response(
    bundle_household: dict[str, object] | None,
    members: list[dict[str, object]],
    *,
    active_household_id: str | None = None,
) -> HouseholdBundleResponse:
    """Wrap household and membership state into the common bundle response."""
    return HouseholdBundleResponse(
        household=(household_response(bundle_household) if bundle_household is not None else None),
        members=[household_member_response(item) for item in members],
        active_household_id=active_household_id,
    )


def household_invite_response(invite: dict[str, object]) -> HouseholdInviteResponseItem:
    """Convert a persisted household invite into the API response model."""
    return HouseholdInviteResponseItem(
        invite_id=str(invite["invite_id"]),
        household_id=str(invite["household_id"]),
        code=str(invite["code"]),
        created_by_user_id=str(invite["created_by_user_id"]),
        created_at=datetime.fromisoformat(str(invite["created_at"])),
        expires_at=datetime.fromisoformat(str(invite["expires_at"])),
        max_uses=int(invite["max_uses"]),  # type: ignore[arg-type]
        uses=int(invite["uses"]),  # type: ignore[arg-type]
    )


def map_household_error(
    exc: Exception,
    *,
    not_found_message: str = "household not found",
) -> None:
    """Translate household-domain exceptions into API errors."""
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


# ---------------------------------------------------------------------------
# Access checks and care-context helpers
# ---------------------------------------------------------------------------

def ensure_household_subject_access(
    *,
    context: AppContext,
    household_id: str,
    viewer_user_id: str,
    subject_user_id: str | None = None,
) -> None:
    """Ensure the viewer can read household care data for the requested subject."""
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


def build_care_context(
    *, household_id: str, viewer_user_id: str, subject_user_id: str
) -> HouseholdCareContextResponse:
    """Build the standard care-context envelope shared by household care responses."""
    return HouseholdCareContextResponse(
        viewer_user_id=viewer_user_id,
        subject_user_id=subject_user_id,
        household_id=household_id,
    )


# ---------------------------------------------------------------------------
# Core API service orchestration (lifecycle ops)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Caregiver-facing aggregates
# ---------------------------------------------------------------------------

def list_household_care_members(
    *,
    context: AppContext,
    household_id: str,
    viewer_user_id: str,
) -> HouseholdCareMembersResponse:
    """List members available for caregiver views in the selected household."""
    ensure_household_subject_access(
        context=context,
        household_id=household_id,
        viewer_user_id=viewer_user_id,
    )
    members = context.household_store.list_members(household_id)
    return HouseholdCareMembersResponse(
        viewer_user_id=viewer_user_id,
        household_id=household_id,
        members=[household_member_response(item) for item in members],
    )


def get_household_care_member_profile(
    *,
    context: AppContext,
    household_id: str,
    viewer_user_id: str,
    subject_user_id: str,
) -> HouseholdCareProfileResponse:
    """Read a household member's health profile through caregiver access rules."""
    from apps.api.dietary_api.services._health_profile_support import to_profile_response
    ensure_household_subject_access(
        context=context,
        household_id=household_id,
        viewer_user_id=viewer_user_id,
        subject_user_id=subject_user_id,
    )
    profile = get_or_create_health_profile(context.stores.profiles, subject_user_id)
    completeness = compute_profile_completeness(profile)
    return HouseholdCareProfileResponse(
        context=build_care_context(
            household_id=household_id,
            viewer_user_id=viewer_user_id,
            subject_user_id=subject_user_id,
        ),
        profile=to_profile_response(profile=profile, fallback_mode=completeness.state != "ready"),
    )


def get_household_care_member_daily_summary(
    *,
    context: AppContext,
    household_id: str,
    viewer_user_id: str,
    subject_user_id: str,
    summary_date: Any,
) -> HouseholdCareMealSummaryResponse:
    """Read a household member's daily meal summary through caregiver access rules."""
    from apps.api.dietary_api.deps import MealDeps
    from apps.api.dietary_api.services.meals import get_daily_summary
    ensure_household_subject_access(
        context=context,
        household_id=household_id,
        viewer_user_id=viewer_user_id,
        subject_user_id=subject_user_id,
    )
    summary = get_daily_summary(
        deps=MealDeps(
            settings=context.settings,
            stores=context.stores,
            coordinator=context.coordinator,
        ),
        user_id=subject_user_id,
        summary_date=summary_date,
    )
    return HouseholdCareMealSummaryResponse(
        context=build_care_context(
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
    """Read a household member's reminders through caregiver access rules."""
    from apps.api.dietary_api.services.reminders import list_reminders_for_session
    ensure_household_subject_access(
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
        context=build_care_context(
            household_id=household_id,
            viewer_user_id=viewer_user_id,
            subject_user_id=subject_user_id,
        ),
        reminders=reminder_list.reminders,
        metrics=reminder_list.metrics,
    )
