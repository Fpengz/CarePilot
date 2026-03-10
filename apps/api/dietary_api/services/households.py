"""Public household API service facade.

.. deprecated::
    Thin re-export shim. All logic lives in
    ``dietary_guardian.application.household.use_cases``.
"""

from __future__ import annotations

from dietary_guardian.application.household.use_cases import (  # noqa: F401
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

__all__ = [
    "create_household",
    "create_household_invite",
    "get_current_household",
    "get_household_care_member_daily_summary",
    "get_household_care_member_profile",
    "join_household",
    "leave_household",
    "list_household_care_member_reminders",
    "list_household_care_members",
    "list_household_members",
    "remove_household_member",
    "rename_household",
    "set_active_household",
]
