from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol, cast

from dietary_guardian.models.health_profile import HealthProfileRecord, ProfileCompleteness
from dietary_guardian.models.identity import AccountRole
from dietary_guardian.models.user import UserProfile
from dietary_guardian.services.authorization import default_profile_mode_for_role

DEFAULT_PROFILE_AGE = 68


class HealthProfileRepository(Protocol):
    def get_health_profile(self, user_id: str) -> HealthProfileRecord | None: ...

    def save_health_profile(self, profile: HealthProfileRecord) -> HealthProfileRecord: ...


def default_health_profile(user_id: str) -> HealthProfileRecord:
    return HealthProfileRecord(user_id=user_id)


def compute_profile_completeness(profile: HealthProfileRecord) -> ProfileCompleteness:
    missing: list[str] = []
    if not profile.conditions:
        missing.append("conditions")
    if not profile.nutrition_goals:
        missing.append("nutrition_goals")
    if not profile.preferred_cuisines:
        missing.append("preferred_cuisines")
    if not profile.age:
        missing.append("age")
    if profile.locale.strip() == "":
        missing.append("locale")
    if len(missing) >= 4:
        state = "needs_profile"
    elif missing:
        state = "partial"
    else:
        state = "ready"
    return ProfileCompleteness(state=state, missing_fields=missing)


def get_or_create_health_profile(repository: HealthProfileRepository, user_id: str) -> HealthProfileRecord:
    stored = repository.get_health_profile(user_id)
    if stored is not None:
        return stored
    return default_health_profile(user_id)


def update_health_profile(
    repository: HealthProfileRepository,
    *,
    user_id: str,
    updates: dict[str, Any],
) -> HealthProfileRecord:
    current = get_or_create_health_profile(repository, user_id)
    merged_payload = {
        **current.model_dump(mode="json"),
        **updates,
        "user_id": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    merged = HealthProfileRecord.model_validate(merged_payload)
    return repository.save_health_profile(merged)


def build_user_profile_from_health_profile(
    *,
    session: dict[str, Any],
    health_profile: HealthProfileRecord,
) -> UserProfile:
    return UserProfile(
        id=str(session["user_id"]),
        name=str(session["display_name"]),
        age=int(health_profile.age or DEFAULT_PROFILE_AGE),
        conditions=list(health_profile.conditions),
        medications=list(health_profile.medications),
        profile_mode=session.get("profile_mode")
        or default_profile_mode_for_role(cast(AccountRole, str(session["account_role"]))),
        locale=health_profile.locale,
        allergies=list(health_profile.allergies),
        nutrition_goals=list(health_profile.nutrition_goals),
        preferred_cuisines=list(health_profile.preferred_cuisines),
        disliked_ingredients=list(health_profile.disliked_ingredients),
        budget_tier=health_profile.budget_tier,
        target_calories_per_day=health_profile.target_calories_per_day,
        macro_focus=list(health_profile.macro_focus),
        daily_sodium_limit_mg=health_profile.daily_sodium_limit_mg,
        daily_sugar_limit_g=health_profile.daily_sugar_limit_g,
        daily_protein_target_g=health_profile.daily_protein_target_g,
        daily_fiber_target_g=health_profile.daily_fiber_target_g,
    )


def resolve_user_profile(
    repository: HealthProfileRepository,
    session: dict[str, Any],
) -> tuple[HealthProfileRecord, UserProfile]:
    health_profile = get_or_create_health_profile(repository, str(session["user_id"]))
    return health_profile, build_user_profile_from_health_profile(session=session, health_profile=health_profile)


def compute_bmi(profile: HealthProfileRecord) -> float | None:
    if profile.height_cm is None or profile.weight_kg is None or profile.height_cm <= 0:
        return None
    height_m = profile.height_cm / 100.0
    return round(profile.weight_kg / (height_m * height_m), 2)
