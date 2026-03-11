"""Shared response and error helpers for household API services.

.. deprecated::
    Thin re-export shim. All logic lives in
    ``dietary_guardian.application.household.use_cases``.
"""

from __future__ import annotations

from dietary_guardian.application.household.use_cases import (  # noqa: F401
    household_bundle_response,
    household_invite_response,
    household_member_response,
    household_response,
    map_household_error,
)

__all__ = [
    "household_bundle_response",
    "household_invite_response",
    "household_member_response",
    "household_response",
    "map_household_error",
]
