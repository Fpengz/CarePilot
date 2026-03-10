"""Public household API service facade.

This module keeps the router import surface stable while the implementation is
split into lifecycle, access, and care-context helpers.
"""

from __future__ import annotations

from apps.api.dietary_api.services.households_care import (
    get_household_care_member_daily_summary,
    get_household_care_member_profile,
    list_household_care_member_reminders,
    list_household_care_members,
)
from apps.api.dietary_api.services.households_core import (
    create_household,
    create_household_invite,
    get_current_household,
    join_household,
    leave_household,
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
