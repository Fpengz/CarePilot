from __future__ import annotations

from dietary_guardian.domain.care import CaseSnapshot
from dietary_guardian.domain.health.models import (
    BiomarkerReading,
    ClinicalProfileSnapshot,
    HealthProfileRecord,
    MedicationAdherenceEvent,
    SymptomCheckIn,
)
from dietary_guardian.domain.identity.models import UserProfile
from dietary_guardian.domain.notifications.models import ReminderEvent
from dietary_guardian.domain.nutrition import (
    meal_confidence,
    meal_display_name,
    meal_identification_method,
    meal_nutrition,
)
from dietary_guardian.models.meal_record import MealRecognitionRecord


def _meal_is_risky(record: MealRecognitionRecord) -> bool:
    nutrition = meal_nutrition(record)
    return (
        float(nutrition.sodium_mg) >= 900.0
        or float(nutrition.sugar_g) >= 18.0
        or float(nutrition.calories) >= 700.0
        or meal_identification_method(record) == "User_Manual"
        or meal_confidence(record) < 0.75
    )


def _meal_risk_streak(meals: list[MealRecognitionRecord]) -> int:
    streak = 0
    for record in reversed(meals):
        if not _meal_is_risky(record):
            break
        streak += 1
    return streak


def _adherence_rate(events: list[MedicationAdherenceEvent]) -> float | None:
    if not events:
        return None
    taken = sum(1 for item in events if item.status == "taken")
    return round(taken / len(events), 4)


def _reminder_response_rate(reminders: list[ReminderEvent]) -> float:
    if not reminders:
        return 0.0
    responded = sum(1 for item in reminders if item.meal_confirmation in {"yes", "no"})
    return round(responded / len(reminders), 4)


def _average_symptom_severity(symptoms: list[SymptomCheckIn]) -> float:
    if not symptoms:
        return 0.0
    return round(sum(item.severity for item in symptoms) / len(symptoms), 4)


def build_case_snapshot(
    *,
    user_profile: UserProfile,
    health_profile: HealthProfileRecord | None,
    meals: list[MealRecognitionRecord],
    reminders: list[ReminderEvent],
    adherence_events: list[MedicationAdherenceEvent],
    symptoms: list[SymptomCheckIn],
    biomarker_readings: list[BiomarkerReading],
    clinical_snapshot: ClinicalProfileSnapshot | None,
) -> CaseSnapshot:
    biomarker_summary = (
        dict(clinical_snapshot.biomarkers)
        if clinical_snapshot is not None
        else {item.name: float(item.value) for item in biomarker_readings}
    )
    active_risk_flags = list(clinical_snapshot.risk_flags) if clinical_snapshot is not None else []
    if any(item.safety.decision == "escalate" for item in symptoms):
        active_risk_flags.append("symptom_escalation")
    adherence_rate = _adherence_rate(adherence_events)
    if adherence_rate is not None and adherence_rate < 0.7:
        active_risk_flags.append("low_adherence")
    reminder_response_rate = _reminder_response_rate(reminders)
    if reminders and reminder_response_rate == 0.0:
        active_risk_flags.append("no_reminder_response")

    condition_names = [item.name for item in user_profile.conditions]
    if health_profile is not None and not condition_names:
        condition_names = [item.name for item in health_profile.conditions]

    medication_names = [item.name for item in user_profile.medications]
    if health_profile is not None and not medication_names:
        medication_names = [item.name for item in health_profile.medications]

    latest_meal_name = meal_display_name(meals[-1]) if meals else None
    return CaseSnapshot(
        user_id=user_profile.id,
        profile_name=user_profile.name,
        conditions=condition_names,
        medications=medication_names,
        meal_count=len(meals),
        latest_meal_name=latest_meal_name,
        meal_risk_streak=_meal_risk_streak(meals),
        reminder_count=len(reminders),
        reminder_response_rate=reminder_response_rate,
        adherence_events=len(adherence_events),
        adherence_rate=adherence_rate,
        symptom_count=len(symptoms),
        average_symptom_severity=_average_symptom_severity(symptoms),
        biomarker_summary=biomarker_summary,
        active_risk_flags=sorted(set(active_risk_flags)),
    )
