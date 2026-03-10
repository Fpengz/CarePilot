"""Access checks and care-context helpers for household API services.

.. deprecated::
    Thin re-export shim. All logic lives in
    ``dietary_guardian.application.household.use_cases``.
"""

from __future__ import annotations

from dietary_guardian.application.household.use_cases import (  # noqa: F401
    build_care_context,
    ensure_household_subject_access,
)

__all__ = ["build_care_context", "ensure_household_subject_access"]
