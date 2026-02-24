from dietary_guardian.models.meal import MealState
from dietary_guardian.models.role_tools import (
    CaregiverToolState,
    ClinicianToolState,
    PatientToolState,
)
from dietary_guardian.models.user import UserProfile, UserRole


def get_role_sections(role: UserRole) -> list[str]:
    return [role]


def build_patient_tool_state(history: list[MealState]) -> PatientToolState:
    recent = history[-5:]
    reminders_due = len(recent) > 0
    return PatientToolState(
        recent_meal_names=[meal.dish_name for meal in recent],
        after_meal_reminder_due=reminders_due,
        meal_confirmation_rate=1.0 if recent else None,
    )


def build_caregiver_tool_state(history: list[MealState]) -> CaregiverToolState:
    alerts: list[str] = []
    manual_review_count = 0
    for meal in history:
        if meal.identification_method == "User_Manual" or meal.confidence_score < 0.75:
            manual_review_count += 1
            alerts.append(f"{meal.dish_name}: manual review required.")
        if meal.nutrition.sodium_mg >= 1000:
            alerts.append(
                f"{meal.dish_name}: high sodium ({meal.nutrition.sodium_mg:.0f}mg)."
            )
    return CaregiverToolState(
        high_risk_alert_count=len(alerts),
        manual_review_count=manual_review_count,
        alerts=alerts,
    )


def build_clinician_tool_state(
    user: UserProfile,
    history: list[MealState],
    biomarkers: dict[str, float],
) -> ClinicianToolState:
    latest_meal = history[-1].dish_name if history else "No meal analyzed"
    biomarker_text = ", ".join(f"{k}={v}" for k, v in biomarkers.items()) or "No biomarkers"
    narrative = (
        f"Patient {user.name}: latest meal '{latest_meal}'. "
        f"Biomarker grounding: {biomarker_text}."
    )
    payload = {
        "patient_id": user.id,
        "patient_name": user.name,
        "latest_meal": latest_meal,
        "biomarkers": biomarkers,
        "recommendation_basis": "Meal analysis + biomarker grounding",
    }
    return ClinicianToolState(
        biomarker_summary=biomarkers,
        narrative=narrative,
        export_payload=payload,
    )
