"""API compatibility layer for auth/session helpers.

This module keeps the existing import surface used by API routers/tests while the
auth implementation is moved under `dietary_guardian.infrastructure.auth`.
"""

from typing import Any, cast

from dietary_guardian.infrastructure.auth import AuthUserRecord, InMemoryAuthStore, SessionSigner
from dietary_guardian.models.identity import AccountRole, ProfileMode
from dietary_guardian.models.user import MedicalCondition, Medication, UserProfile
from dietary_guardian.services.authorization import default_profile_mode_for_role


def build_user_profile_from_session(session: dict[str, Any]) -> UserProfile:
    # Minimal profile for coordinator/authz contexts; domain-rich data can be loaded later.
    return UserProfile(
        id=str(session["user_id"]),
        name=str(session["display_name"]),
        age=68,
        conditions=[MedicalCondition(name="Diabetes", severity="High")],
        medications=[Medication(name="Warfarin", dosage="5mg")],
        profile_mode=cast(
            ProfileMode,
            session.get("profile_mode")
            or default_profile_mode_for_role(cast(AccountRole, session["account_role"])),
        ),
    )


__all__ = [
    "AuthUserRecord",
    "InMemoryAuthStore",
    "SessionSigner",
    "build_user_profile_from_session",
]

