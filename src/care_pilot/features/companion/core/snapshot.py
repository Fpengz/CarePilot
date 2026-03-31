"""
Implement case snapshot use cases.

This module assembles the companion case snapshot used by downstream
personalization and engagement workflows.
"""

from __future__ import annotations

from datetime import UTC, datetime

from care_pilot.features.companion.core.domain import PatientCaseSnapshot
from care_pilot.features.companion.core.health.blood_pressure import summarize_blood_pressure
from care_pilot.features.companion.core.health.models import (
    BiomarkerReading,
    BloodPressureReading,
    BloodPressureSummary,
    ClinicalProfileSnapshot,
    HealthProfileRecord,
    MedicationAdherenceEvent,
    SymptomCheckIn,
)
from care_pilot.features.companion.core.pruning import PruningService
from care_pilot.features.meals.domain import (
    meal_confidence,
    meal_display_name,
    meal_identification_method,
    meal_nutrition,
)
from care_pilot.features.meals.domain.recognition import MealRecognitionRecord
from care_pilot.features.profiles.domain.models import UserProfile
from care_pilot.features.reminders.domain.models import ReminderEvent


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
    blood_pressure_readings: list[BloodPressureReading],
    clinical_snapshot: ClinicalProfileSnapshot | None,
) -> PatientCaseSnapshot:
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
    bp_summary = summarize_blood_pressure(blood_pressure_readings, conditions=condition_names)
    if bp_summary and bp_summary.has_high_bp:
        active_risk_flags.append("high_bp")

    # Map complex fields
    recent_meals = [
        {
            "name": meal_display_name(m),
            "captured_at": str(m.captured_at),
            "is_risky": _meal_is_risky(m),
        }
        for m in meals
    ]
    recent_symptoms = [
        {"severity": s.severity, "recorded_at": str(s.recorded_at), "decision": s.safety.decision}
        for s in symptoms
    ]

    snapshot = PatientCaseSnapshot(
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
        blood_pressure_summary=bp_summary,
        recent_meals=recent_meals,
        recent_symptoms=recent_symptoms,
        demographics={
            "age": health_profile.age if health_profile else None,
            "height_cm": health_profile.height_cm if health_profile else None,
            "weight_kg": health_profile.weight_kg if health_profile else None,
        },
    )

    # Apply pruning
    pruner = PruningService()
    return pruner.prune(snapshot)


def load_snapshot_from_sections(
    *, user_id: str, eventing_store
) -> PatientCaseSnapshot | None:
    sections = eventing_store.list_snapshot_sections(user_id=user_id)
    if not sections:
        return None
    section_map = {section.section_key: section for section in sections}
    required = {
        "demographics",
        "medications_adherence",
        "meals_nutrition",
        "trends_vitals",
        "conversation_summary",
    }
    if not required.issubset(section_map.keys()):
        return None

    demographics = section_map["demographics"].payload
    meds = section_map["medications_adherence"].payload
    meals = section_map["meals_nutrition"].payload
    trends = section_map["trends_vitals"].payload
    conversation = section_map["conversation_summary"].payload

    bp_summary_payload = trends.get("blood_pressure_summary")
    bp_summary = (
        BloodPressureSummary.model_validate(bp_summary_payload)
        if bp_summary_payload
        else None
    )
    last_interaction_at = conversation.get("last_interaction_at")
    if isinstance(last_interaction_at, str):
        try:
            last_interaction_at = datetime.fromisoformat(last_interaction_at)
        except ValueError:
            last_interaction_at = None

    return PatientCaseSnapshot(
        user_id=user_id,
        profile_name=str(demographics.get("profile_name") or "Patient"),
        demographics=dict(demographics.get("demographics") or {}),
        conditions=list(demographics.get("conditions") or []),
        medications=list(meds.get("medications") or []),
        goals=list(demographics.get("goals") or []),
        clinician_instructions=list(demographics.get("clinician_instructions") or []),
        meal_count=int(meals.get("meal_count") or 0),
        latest_meal_name=meals.get("latest_meal_name"),
        meal_risk_streak=int(meals.get("meal_risk_streak") or 0),
        reminder_count=int(meds.get("reminder_count") or 0),
        reminder_response_rate=float(meds.get("reminder_response_rate") or 0.0),
        adherence_events=int(meds.get("adherence_events") or 0),
        adherence_rate=meds.get("adherence_rate"),
        symptom_count=int(conversation.get("symptom_count") or 0),
        average_symptom_severity=float(conversation.get("average_symptom_severity") or 0.0),
        recent_meals=list(meals.get("recent_meals") or []),
        recent_symptoms=list(conversation.get("recent_symptoms") or []),
        recent_emotion_markers=list(conversation.get("recent_emotion_markers") or []),
        biomarker_summary=dict(trends.get("biomarker_summary") or {}),
        blood_pressure_summary=bp_summary,
        active_risk_flags=list(trends.get("active_risk_flags") or []),
        trends=dict(trends.get("trends") or {}),
        current_conversation_turn=int(conversation.get("current_conversation_turn") or 0),
        pending_tasks=list(conversation.get("pending_tasks") or []),
        unresolved_questions=list(conversation.get("unresolved_questions") or []),
        last_interaction_at=last_interaction_at,
        generated_at=datetime.now(UTC),
    )


def build_case_snapshot_prefer_projection(
    *,
    user_id: str,
    eventing_store,
    user_profile: UserProfile,
    health_profile: HealthProfileRecord | None,
    meals: list[MealRecognitionRecord],
    reminders: list[ReminderEvent],
    adherence_events: list[MedicationAdherenceEvent],
    symptoms: list[SymptomCheckIn],
    biomarker_readings: list[BiomarkerReading],
    blood_pressure_readings: list[BloodPressureReading],
    clinical_snapshot: ClinicalProfileSnapshot | None,
) -> PatientCaseSnapshot:
    if eventing_store is not None:
        snapshot = load_snapshot_from_sections(user_id=user_id, eventing_store=eventing_store)
        if snapshot is not None:
            return snapshot
    return build_case_snapshot(
        user_profile=user_profile,
        health_profile=health_profile,
        meals=meals,
        reminders=reminders,
        adherence_events=adherence_events,
        symptoms=symptoms,
        biomarker_readings=biomarker_readings,
        blood_pressure_readings=blood_pressure_readings,
        clinical_snapshot=clinical_snapshot,
    )
