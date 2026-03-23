"""Shared response helpers for health-profile API services.

Shim: business logic lives in care_pilot.features.profiles.profile_service.
"""

from __future__ import annotations

from care_pilot.features.profiles.profile_service import to_profile_response  # noqa: F401

__all__ = ["to_profile_response"]
