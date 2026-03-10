"""Shared response and error helpers for household API services."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, cast

from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    HouseholdBundleResponse,
    HouseholdInviteResponseItem,
    HouseholdMemberItem,
    HouseholdResponse,
)
from dietary_guardian.application.household import (
    HouseholdAlreadyExistsError,
    HouseholdForbiddenError,
    HouseholdInviteInvalidError,
    HouseholdMembershipConflictError,
    HouseholdNotFoundError,
    HouseholdOwnerLeaveForbiddenError,
)


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


__all__ = [
    "household_bundle_response",
    "household_invite_response",
    "household_member_response",
    "household_response",
    "map_household_error",
]
