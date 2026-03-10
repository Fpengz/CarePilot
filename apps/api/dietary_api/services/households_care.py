"""Caregiver-facing household aggregates that span profile, meal, and reminder data."""

from __future__ import annotations

from apps.api.dietary_api.deps import AppContext, MealDeps
from apps.api.dietary_api.schemas import (
    HouseholdCareMealSummaryResponse,
    HouseholdCareMembersResponse,
    HouseholdCareProfileResponse,
    HouseholdCareReminderListResponse,
)
from apps.api.dietary_api.services._health_profile_support import to_profile_response
from apps.api.dietary_api.services.households_access import (
    build_care_context,
    ensure_household_subject_access,
)
from apps.api.dietary_api.services.households_support import household_member_response
from apps.api.dietary_api.services.meals import get_daily_summary
from apps.api.dietary_api.services.reminders import list_reminders_for_session
from dietary_guardian.domain.profiles.health_profile import (
    compute_profile_completeness,
    get_or_create_health_profile,
)


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
    summary_date,
) -> HouseholdCareMealSummaryResponse:
    """Read a household member's daily meal summary through caregiver access rules."""
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


__all__ = [
    "get_household_care_member_daily_summary",
    "get_household_care_member_profile",
    "list_household_care_member_reminders",
    "list_household_care_members",
]
