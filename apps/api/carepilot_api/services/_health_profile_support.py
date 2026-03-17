"""Shared response helpers for health-profile API services.

Shim: business logic lives in care_pilot.features.profiles.profile_service.
"""

from __future__ import annotations

from care_pilot.features.profiles.profile_service import (  # noqa: F401
    to_profile_response,
)

__all__ = ["to_profile_response"]
