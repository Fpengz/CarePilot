from typing import Literal

from dietary_guardian.application.personalization.profile_tools import (
    build_caregiver_tool_state,
    build_clinical_summary_tool_state,
    build_self_tool_state,
    get_profile_sections,
)
from dietary_guardian.domain.identity.models import (
    MedicalCondition,
    Medication,
    UserProfile,
)
from dietary_guardian.models.meal import MealState, Nutrition
from dietary_guardian.models.profile_tools import (
    CaregiverToolState,
    ClinicalSummaryToolState,
    SelfToolState,
)


def _make_state(
    dish_name: str,
    sodium_mg: float,
    confidence: float = 0.9,
    method: Literal["AI_Flash", "HPB_Fallback", "User_Manual"] = "AI_Flash",
) -> MealState:
    return MealState(
        dish_name=dish_name,
        confidence_score=confidence,
        identification_method=method,
        ingredients=[],
        nutrition=Nutrition(
            calories=500,
            carbs_g=60,
            sugar_g=8,
            protein_g=20,
            fat_g=15,
            sodium_mg=sodium_mg,
        ),
    )


def test_profile_sections_are_gated() -> None:
    assert get_profile_sections("self") == ["self"]
    assert get_profile_sections("caregiver") == ["caregiver"]


def test_self_tool_state_contains_recent_meals() -> None:
    meals = [_make_state("Laksa", 1500), _make_state("Yong Tau Foo", 700)]
    state = build_self_tool_state(meals)

    assert isinstance(state, SelfToolState)
    assert state.recent_meal_names == ["Laksa", "Yong Tau Foo"]
    assert state.after_meal_reminder_due is True


def test_caregiver_tool_state_detects_high_risk_alerts() -> None:
    meals = [
        _make_state("Laksa", 1500),
        _make_state("Unknown", 200, confidence=0.3, method="User_Manual"),
    ]
    state = build_caregiver_tool_state(meals)

    assert isinstance(state, CaregiverToolState)
    assert state.high_risk_alert_count == 2
    assert len(state.alerts) == 2


def test_clinical_summary_tool_state_has_export_payload() -> None:
    profile = UserProfile(
        id="u1",
        name="Mr. Tan",
        age=68,
        conditions=[MedicalCondition(name="Diabetes", severity="High")],
        medications=[Medication(name="Warfarin", dosage="5mg")],
        profile_mode="caregiver",
    )
    meals = [_make_state("Laksa", 1500)]
    biomarkers = {"LDL": 4.2, "HbA1c": 7.1}
    state = build_clinical_summary_tool_state(profile, meals, biomarkers)

    assert isinstance(state, ClinicalSummaryToolState)
    assert state.export_payload["subject_name"] == "Mr. Tan"
    assert state.export_payload["biomarkers"]["LDL"] == 4.2
