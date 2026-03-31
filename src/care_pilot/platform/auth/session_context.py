"""
Build session-derived profile context.

This module constructs profile context objects from authenticated sessions
for downstream use cases.
"""

from typing import Any, cast

from care_pilot.features.profiles.domain.health_profile import (
    HealthProfileRepository,
    build_user_profile_from_health_profile,
    default_health_profile,
)
from care_pilot.features.profiles.domain.models import AccountRole, ProfileMode, UserProfile
from care_pilot.platform.observability.tooling.domain.authorization import (
    default_profile_mode_for_role,
)


def build_user_profile_from_session(
    session: dict[str, Any],
    repository: HealthProfileRepository | None = None,
) -> UserProfile:
    health_profile = (
        repository.get_health_profile(str(session["user_id"])) if repository is not None else None
    ) or default_health_profile(str(session["user_id"]))
    profile = build_user_profile_from_health_profile(session=session, health_profile=health_profile)
    profile.profile_mode = cast(
        ProfileMode,
        session.get("profile_mode")
        or default_profile_mode_for_role(cast(AccountRole, session["account_role"])),
    )
    return profile
