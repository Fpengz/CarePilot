"""Shared response helpers for health-profile API services.

Shim: business logic lives in care_pilot.features.profiles.use_cases.
"""

from __future__ import annotations

from care_pilot.features.profiles.use_cases import (  # noqa: F401
    to_profile_response,
)

__all__ = ["to_profile_response"]
