"""Access checks and care-context helpers for household API services."""

from __future__ import annotations

from dietary_guardian.application.policies.household_access import (
    HouseholdAccessNotFoundError,
    ensure_household_member,
)

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import HouseholdCareContextResponse


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



def build_care_context(*, household_id: str, viewer_user_id: str, subject_user_id: str) -> HouseholdCareContextResponse:
    """Build the standard care-context envelope shared by household care responses."""
    return HouseholdCareContextResponse(
        viewer_user_id=viewer_user_id,
        subject_user_id=subject_user_id,
        household_id=household_id,
    )


__all__ = ["build_care_context", "ensure_household_subject_access"]
