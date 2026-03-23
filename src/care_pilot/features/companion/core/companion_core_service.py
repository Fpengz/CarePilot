"""
Implement companion interaction orchestration.

This module coordinates core companion workflows and interaction handling.
"""

from __future__ import annotations

from dataclasses import dataclass

from care_pilot.features.companion.care_plans.care_plan import compose_care_plan
from care_pilot.features.companion.clinician_digest.digest import build_clinician_digest
from care_pilot.features.companion.core.domain import (
    CaseSnapshot,
    ClinicianDigest,
    CompanionInteraction,
    CompanionInteractionResult,
    EngagementAssessment,
    ImpactSummary,
    PersonalizationContext,
)
from care_pilot.features.companion.core.evidence import (
    EvidenceRetrievalPort,
    retrieve_supporting_evidence,
)
from care_pilot.features.companion.core.health.models import (
    BiomarkerReading,
    BloodPressureReading,
    ClinicalProfileSnapshot,
    HealthProfileRecord,
    MedicationAdherenceEvent,
    SymptomCheckIn,
)
from care_pilot.features.companion.core.snapshot import build_case_snapshot
from care_pilot.features.companion.engagement.engagement import assess_engagement
from care_pilot.features.companion.impact.impact import build_impact_summary
from care_pilot.features.companion.personalization.personalization import (
    build_personalization_context,
)
from care_pilot.features.meals.domain.recognition import MealRecognitionRecord
from care_pilot.features.profiles.domain.models import UserProfile
from care_pilot.features.reminders.domain.models import ReminderEvent
from care_pilot.features.safety.safety_engine import apply_safety_decision, review_care_plan


@dataclass(frozen=True, slots=True)
class CompanionStateInputs:
    user_profile: UserProfile
    health_profile: HealthProfileRecord | None
    meals: list[MealRecognitionRecord]
    reminders: list[ReminderEvent]
    adherence_events: list[MedicationAdherenceEvent]
    symptoms: list[SymptomCheckIn]
    biomarker_readings: list[BiomarkerReading]
    blood_pressure_readings: list[BloodPressureReading]
    clinical_snapshot: ClinicalProfileSnapshot | None
    emotion_signal: str | None


@dataclass(frozen=True, slots=True)
class CompanionRuntimeState:
    snapshot: CaseSnapshot
    personalization: PersonalizationContext
    engagement: EngagementAssessment


def build_companion_runtime_state(
    *,
    interaction: CompanionInteraction,
    inputs: CompanionStateInputs,
) -> CompanionRuntimeState:
    snapshot = build_case_snapshot(
        user_profile=inputs.user_profile,
        health_profile=inputs.health_profile,
        meals=inputs.meals,
        reminders=inputs.reminders,
        adherence_events=inputs.adherence_events,
        symptoms=inputs.symptoms,
        biomarker_readings=inputs.biomarker_readings,
        blood_pressure_readings=inputs.blood_pressure_readings,
        clinical_snapshot=inputs.clinical_snapshot,
    )
    personalization = build_personalization_context(
        interaction_type=interaction.interaction_type,
        message=interaction.message,
        user_profile=inputs.user_profile,
        health_profile=inputs.health_profile,
        snapshot=snapshot,
        emotion_signal=inputs.emotion_signal,
    )
    engagement = assess_engagement(snapshot=snapshot, emotion_signal=inputs.emotion_signal)
    return CompanionRuntimeState(
        snapshot=snapshot,
        personalization=personalization,
        engagement=engagement,
    )


def run_companion_interaction(
    *,
    interaction: CompanionInteraction,
    inputs: CompanionStateInputs,
    evidence_retriever: EvidenceRetrievalPort,
) -> CompanionInteractionResult:
    runtime = build_companion_runtime_state(interaction=interaction, inputs=inputs)
    evidence = retrieve_supporting_evidence(
        retriever=evidence_retriever,
        interaction_type=interaction.interaction_type,
        message=interaction.message,
        snapshot=runtime.snapshot,
        personalization=runtime.personalization,
    )
    care_plan = compose_care_plan(
        interaction=interaction,
        snapshot=runtime.snapshot,
        personalization=runtime.personalization,
        engagement=runtime.engagement,
        evidence=evidence,
    )
    safety = review_care_plan(
        interaction=interaction,
        snapshot=runtime.snapshot,
        engagement=runtime.engagement,
        care_plan=care_plan,
    )
    care_plan = apply_safety_decision(care_plan=care_plan, decision=safety)
    digest = build_clinician_digest(
        interaction=interaction,
        snapshot=runtime.snapshot,
        engagement=runtime.engagement,
        care_plan=care_plan,
        evidence=evidence,
        safety=safety,
    )
    impact = build_impact_summary(
        snapshot=runtime.snapshot,
        engagement=runtime.engagement,
        interaction=interaction,
        interventions=care_plan.recommended_actions,
    )
    return CompanionInteractionResult(
        interaction=interaction,
        snapshot=runtime.snapshot,
        engagement=runtime.engagement,
        care_plan=care_plan,
        clinician_digest_preview=digest,
        impact=impact,
        evidence=evidence,
        safety=safety,
    )


def build_companion_today_bundle(
    *,
    inputs: CompanionStateInputs,
    evidence_retriever: EvidenceRetrievalPort,
) -> tuple[
    CaseSnapshot,
    EngagementAssessment,
    PersonalizationContext,
    ClinicianDigest,
    ImpactSummary,
    CompanionInteractionResult,
]:
    synthetic_interaction = CompanionInteraction(
        interaction_type="check_in",
        message="Summarize today's most important next step.",
        request_id="today",
        correlation_id="today",
        emotion_signal=inputs.emotion_signal,
    )
    result = run_companion_interaction(
        interaction=synthetic_interaction,
        inputs=inputs,
        evidence_retriever=evidence_retriever,
    )
    runtime = build_companion_runtime_state(interaction=synthetic_interaction, inputs=inputs)
    return (
        result.snapshot,
        result.engagement,
        runtime.personalization,
        result.clinician_digest_preview,
        result.impact,
        result,
    )
