"""Application module for daily suggestions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone

from dietary_guardian.domain.health.models import (
    BiomarkerReading,
    ClinicalProfileSnapshot,
    HealthProfileRecord,
)
from dietary_guardian.domain.identity.models import UserProfile
from dietary_guardian.domain.recommendations.models import (
    DailySuggestionBundle,
    DailySuggestionItem,
)
from dietary_guardian.infrastructure.observability import get_logger
from dietary_guardian.domain.meals.recognition import MealRecognitionRecord

logger = get_logger(__name__)


@dataclass(frozen=True)
class MealCandidate:
    slot: str
    title: str
    venue_type: str
    cuisines: tuple[str, ...]
    traits: tuple[str, ...]
    ingredients: tuple[str, ...] = field(default_factory=tuple)
    caution_notes: tuple[str, ...] = field(default_factory=tuple)


SINGAPORE_CANDIDATES: tuple[MealCandidate, ...] = (
    MealCandidate(
        slot="breakfast",
        title="Soft-boiled eggs with wholemeal toast",
        venue_type="kopitiam breakfast set",
        cuisines=("local",),
        traits=("lower_sugar", "heart_health", "lower_sodium"),
        ingredients=("eggs", "wholemeal toast"),
        caution_notes=("Ask for less butter and choose kopi/teh kosong.",),
    ),
    MealCandidate(
        slot="breakfast",
        title="Plain thosai with dhal",
        venue_type="hawker breakfast",
        cuisines=("indian",),
        traits=("heart_health", "lower_sugar", "budget"),
        ingredients=("lentils",),
        caution_notes=("Keep chutney portions modest if sodium intake is a concern.",),
    ),
    MealCandidate(
        slot="lunch",
        title="Sliced fish soup with rice",
        venue_type="hawker stall",
        cuisines=("teochew", "local"),
        traits=("lower_sodium", "heart_health", "high_protein"),
        ingredients=("fish", "vegetables", "rice"),
        caution_notes=("Ask for less soup if you need tighter sodium control.",),
    ),
    MealCandidate(
        slot="lunch",
        title="Thunder tea rice",
        venue_type="food court",
        cuisines=("hakka", "local"),
        traits=("heart_health", "lower_sugar", "high_fiber"),
        ingredients=("vegetables", "tofu", "brown rice"),
        caution_notes=("Request less preserved vegetables to reduce sodium.",),
    ),
    MealCandidate(
        slot="dinner",
        title="Yong tau foo clear soup with tofu and greens",
        venue_type="hawker stall",
        cuisines=("hakka", "local"),
        traits=("lower_sodium", "heart_health", "lower_sugar"),
        ingredients=("tofu", "greens"),
        caution_notes=("Skip fried items and choose fewer fish-ball style pieces.",),
    ),
    MealCandidate(
        slot="dinner",
        title="Steamed chicken rice with extra cucumber",
        venue_type="hawker stall",
        cuisines=("hainanese", "local"),
        traits=("high_protein", "budget"),
        ingredients=("chicken", "rice", "cucumber"),
        caution_notes=("Request less rice and sauce for tighter glucose control.",),
    ),
    MealCandidate(
        slot="snack",
        title="Unsweetened soy milk with nuts",
        venue_type="grab-and-go",
        cuisines=("local",),
        traits=("lower_sugar", "heart_health"),
        ingredients=("soy", "nuts"),
        caution_notes=("Choose unsweetened drinks only.",),
    ),
)


def _latest_snapshot_from_history(readings: Sequence[BiomarkerReading]) -> ClinicalProfileSnapshot | None:
    from dietary_guardian.domain.reports import build_clinical_snapshot

    if not readings:
        return None
    return build_clinical_snapshot(list(readings))


def _contains_restricted_term(candidate: MealCandidate, blocked_terms: set[str]) -> bool:
    searchable = " ".join((candidate.title, " ".join(candidate.ingredients))).lower()
    return any(term and term in searchable for term in blocked_terms)


def _score_candidate(
    candidate: MealCandidate,
    *,
    profile: UserProfile,
    health_profile: HealthProfileRecord,
    snapshot: ClinicalProfileSnapshot | None,
    last_meal_name: str | None,
) -> tuple[float, list[str]]:
    score = 0.45
    why: list[str] = []
    goals = set(goal.lower() for goal in health_profile.nutrition_goals)
    cuisines = set(cuisine.lower() for cuisine in health_profile.preferred_cuisines)
    traits = set(item.lower() for item in candidate.traits)

    matched_goals = sorted(goals.intersection(traits))
    if matched_goals:
        score += 0.18
        why.append(f"Matches your nutrition goals: {', '.join(matched_goals)}.")

    matched_cuisines = sorted(cuisines.intersection(set(item.lower() for item in candidate.cuisines)))
    if matched_cuisines:
        score += 0.12
        why.append(f"Fits your preferred cuisine: {', '.join(matched_cuisines)}.")

    if snapshot is not None:
        biomarkers = snapshot.biomarkers
        if biomarkers.get("hba1c", 0) >= 7.0 and "lower_sugar" in traits:
            score += 0.1
            why.append("Favors steadier glucose control based on recent HbA1c.")
        if biomarkers.get("ldl", 0) >= 3.4 and "heart_health" in traits:
            score += 0.1
            why.append("Supports lower saturated-fat choices based on recent LDL.")
        if biomarkers.get("systolic_bp", 0) >= 140 or biomarkers.get("diastolic_bp", 0) >= 90:
            if "lower_sodium" in traits:
                score += 0.1
                why.append("Leans lower-sodium to match elevated blood-pressure readings.")

    if profile.budget_tier == "budget" and "budget" in traits:
        score += 0.05
        why.append("Stays within a budget-friendly hawker pattern.")

    if last_meal_name and last_meal_name.lower() not in candidate.title.lower():
        score += 0.03
        why.append("Adds variety instead of repeating your most recent meal.")

    if not why:
        why.append("Uses a generally lighter local option while your profile is still incomplete.")
    return min(score, 0.96), why


def build_daily_suggestions(
    *,
    health_profile: HealthProfileRecord,
    user_profile: UserProfile,
    meal_history: Sequence[MealRecognitionRecord],
    biomarker_history: Sequence[BiomarkerReading],
    fallback_mode: bool,
) -> DailySuggestionBundle:
    if health_profile.locale != "en-SG":
        locale = health_profile.locale
    else:
        locale = "en-SG"

    blocked_terms = {item.strip().lower() for item in [*health_profile.allergies, *health_profile.disliked_ingredients] if item.strip()}
    snapshot = _latest_snapshot_from_history(biomarker_history)
    last_meal_name = None
    if meal_history:
        last_item = meal_history[-1]
        meal_state = getattr(last_item, "meal_state", None)
        last_meal_name = getattr(meal_state, "dish_name", None)

    suggestions: dict[str, DailySuggestionItem] = {}
    warnings: list[str] = []
    if fallback_mode:
        warnings.append("Personalization is running in fallback mode until more health profile data is completed.")
    if snapshot is None:
        warnings.append("No recent biomarker snapshot is available, so suggestions use profile-only heuristics.")

    logger.info(
        "daily_suggestions_start user_id=%s locale=%s fallback_mode=%s meal_history_count=%s",
        user_profile.id,
        locale,
        fallback_mode,
        len(meal_history),
    )

    for slot in ("breakfast", "lunch", "dinner"):
        candidates = [candidate for candidate in SINGAPORE_CANDIDATES if candidate.slot == slot]
        ranked: list[tuple[float, MealCandidate, list[str]]] = []
        for candidate in candidates:
            if _contains_restricted_term(candidate, blocked_terms):
                continue
            score, why = _score_candidate(
                candidate,
                profile=user_profile,
                health_profile=health_profile,
                snapshot=snapshot,
                last_meal_name=last_meal_name,
            )
            ranked.append((score, candidate, why))
        if not ranked:
            warnings.append(f"No clean {slot} candidate matched the current restrictions; broaden profile preferences.")
            continue
        ranked.sort(key=lambda item: item[0], reverse=True)
        best_score, best_candidate, why = ranked[0]
        suggestions[slot] = DailySuggestionItem(
            slot=slot,
            title=best_candidate.title,
            venue_type=best_candidate.venue_type,
            why_it_fits=why,
            caution_notes=list(best_candidate.caution_notes),
            confidence=round(best_score - (0.08 if fallback_mode else 0), 2),
        )

    snack_candidate = next((candidate for candidate in SINGAPORE_CANDIDATES if candidate.slot == "snack"), None)
    if snack_candidate is not None and not _contains_restricted_term(snack_candidate, blocked_terms):
        score, why = _score_candidate(
            snack_candidate,
            profile=user_profile,
            health_profile=health_profile,
            snapshot=snapshot,
            last_meal_name=last_meal_name,
        )
        suggestions["snack"] = DailySuggestionItem(
            slot="snack",
            title=snack_candidate.title,
            venue_type=snack_candidate.venue_type,
            why_it_fits=why,
            caution_notes=list(snack_candidate.caution_notes),
            confidence=round(score - (0.08 if fallback_mode else 0), 2),
        )

    bundle = DailySuggestionBundle(
        locale=locale,
        generated_at=datetime.now(timezone.utc).isoformat(),
        warnings=warnings,
        data_sources={
            "meal_history_count": len(meal_history),
            "has_clinical_snapshot": snapshot is not None,
            "biomarker_count": len(biomarker_history),
        },
        suggestions=suggestions,
    )
    logger.info(
        "daily_suggestions_complete user_id=%s locale=%s fallback_mode=%s suggestions=%s warnings=%s",
        user_profile.id,
        locale,
        fallback_mode,
        sorted(bundle.suggestions.keys()),
        len(bundle.warnings),
    )
    return bundle
