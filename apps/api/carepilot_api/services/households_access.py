"""Access checks and care-context helpers for household API services.

.. deprecated::
    Thin re-export shim. All logic lives in
    ``care_pilot.features.households.household_service``.
"""

from __future__ import annotations

from care_pilot.features.households.household_service import (  # noqa: F401
    build_care_context,
    ensure_household_subject_access,
)

__all__ = ["build_care_context", "ensure_household_subject_access"]
