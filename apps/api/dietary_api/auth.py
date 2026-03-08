"""API compatibility layer for auth/session helpers.

This module keeps the existing import surface used by API routers/tests while the
auth implementation is moved under `dietary_guardian.infrastructure.auth`.
"""

from typing import Any, cast

from dietary_guardian.infrastructure.auth import AuthUserRecord, InMemoryAuthStore, SessionSigner
from dietary_guardian.models.identity import AccountRole, ProfileMode
from dietary_guardian.models.user import UserProfile
from dietary_guardian.services.authorization import default_profile_mode_for_role
from dietary_guardian.services.health_profile_service import (
    HealthProfileRepository,
    build_user_profile_from_health_profile,
    default_health_profile,
)


def build_user_profile_from_session(
    session: dict[str, Any],
    repository: HealthProfileRepository | None = None,
) -> UserProfile:
    health_profile = (
        repository.get_health_profile(str(session["user_id"]))
        if repository is not None
        else None
    ) or default_health_profile(str(session["user_id"]))
    profile = build_user_profile_from_health_profile(session=session, health_profile=health_profile)
    profile.profile_mode = cast(
        ProfileMode,
        session.get("profile_mode")
        or default_profile_mode_for_role(cast(AccountRole, session["account_role"])),
    )
    return profile


__all__ = [
    "AuthUserRecord",
    "InMemoryAuthStore",
    "SessionSigner",
    "build_user_profile_from_session",
]
