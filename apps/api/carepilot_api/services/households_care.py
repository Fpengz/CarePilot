"""Caregiver-facing household aggregates that span profile, meal, and reminder data.

.. deprecated::
    Thin re-export shim. All logic lives in
    ``care_pilot.features.households.household_service``.
"""

from __future__ import annotations

from care_pilot.features.households.household_service import (  # noqa: F401
    get_household_care_member_daily_summary,
    get_household_care_member_profile,
    list_household_care_member_reminders,
    list_household_care_members,
)

__all__ = [
    "get_household_care_member_daily_summary",
    "get_household_care_member_profile",
    "list_household_care_member_reminders",
    "list_household_care_members",
]
