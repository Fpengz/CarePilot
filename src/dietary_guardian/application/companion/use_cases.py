"""Application use cases for interactions (companion orchestrator)."""

from __future__ import annotations

from dataclasses import dataclass

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.schemas import (
    ClinicianDigestEnvelopeResponse,
    ClinicianDigestResponse,
    CompanionCarePlanResponse,
    CompanionEngagementResponse,
    CompanionInteractionInfoResponse,
    CompanionInteractionRequest,
    CompanionInteractionResponse,
    CompanionSnapshotResponse,
    CompanionTodayResponse,
    ImpactSummaryPayloadResponse,
    ImpactSummaryResponse,
)
from dietary_guardian.application.companion.care_plan import compose_care_plan
from dietary_guardian.application.companion.digest import build_clinician_digest
from dietary_guardian.application.companion.engagement import assess_engagement
from dietary_guardian.application.companion.impact import build_impact_summary
from dietary_guardian.application.companion.personalization import build_personalization_context
from dietary_guardian.application.companion.snapshot import build_case_snapshot
from dietary_guardian.application.evidence import (
    EvidenceRetrievalPort,
    retrieve_supporting_evidence,
)
from dietary_guardian.application.safety import apply_safety_decision, review_care_plan
from dietary_guardian.domain.companion import (
    CaseSnapshot,
    ClinicianDigest,
    CompanionInteraction,
    CompanionInteractionResult,
    EngagementAssessment,
    ImpactSummary,
    PersonalizationContext,
)
from dietary_guardian.domain.health.models import (
    BiomarkerReading,
    ClinicalProfileSnapshot,
    HealthProfileRecord,
    MedicationAdherenceEvent,
    SymptomCheckIn,
)
from dietary_guardian.domain.identity.models import UserProfile
from dietary_guardian.domain.notifications.models import ReminderEvent
from dietary_guardian.domain.meals.recognition import MealRecognitionRecord
from dietary_guardian.infrastructure.evidence import StaticEvidenceRetriever

_EVIDENCE_RETRIEVER = StaticEvidenceRetriever()


@dataclass(frozen=True, slots=True)
class CompanionStateInputs:
    user_profile: UserProfile
    health_profile: HealthProfileRecord | None
    meals: list[MealRecognitionRecord]
    reminders: list[ReminderEvent]
    adherence_events: list[MedicationAdherenceEvent]
    symptoms: list[SymptomCheckIn]
    biomarker_readings: list[BiomarkerReading]
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
) -> tuple[CaseSnapshot, EngagementAssessment, PersonalizationContext, ClinicianDigest, ImpactSummary, CompanionInteractionResult]:
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


# ---------------------------------------------------------------------------
# API-level orchestration (service layer moved here; Phase 3: decouple schemas)
# ---------------------------------------------------------------------------

def get_companion_today(*, context: AppContext, session: dict[str, object]) -> CompanionTodayResponse:
    """Build the current companion summary for the active session."""
    from dietary_guardian.application.companion.context import load_companion_inputs
    inputs = load_companion_inputs(context=context, session=session)
    snapshot, engagement, _, _, impact, result = build_companion_today_bundle(
        inputs=inputs,
        evidence_retriever=_EVIDENCE_RETRIEVER,
    )
    return CompanionTodayResponse(
        snapshot=CompanionSnapshotResponse.model_validate(snapshot.model_dump(mode="json")),
        engagement=CompanionEngagementResponse.model_validate(engagement.model_dump(mode="json")),
        care_plan=CompanionCarePlanResponse.model_validate(result.care_plan.model_dump(mode="json")),
        impact=ImpactSummaryPayloadResponse.model_validate(impact.model_dump(mode="json")),
    )


def handle_companion_interaction(
    *,
    context: AppContext,
    session: dict[str, object],
    payload: CompanionInteractionRequest,
    request_id: str,
    correlation_id: str,
) -> CompanionInteractionResponse:
    """Run a single companion interaction and return the assembled care outputs."""
    from dietary_guardian.application.companion.context import build_workflow_response, load_companion_inputs
    inputs = load_companion_inputs(
        context=context,
        session=session,
        emotion_text=payload.emotion_text,
    )
    context.event_timeline.append(
        event_type="workflow_started",
        workflow_name="companion_interaction",
        request_id=request_id,
        correlation_id=correlation_id,
        user_id=str(session["user_id"]),
        payload={"interaction_type": payload.interaction_type, "has_emotion_text": bool(payload.emotion_text)},
    )
    interaction = CompanionInteraction(
        interaction_type=payload.interaction_type,
        message=payload.message,
        request_id=request_id,
        correlation_id=correlation_id,
        emotion_signal=inputs.emotion_signal,
    )
    result = run_companion_interaction(
        interaction=interaction,
        inputs=inputs,
        evidence_retriever=_EVIDENCE_RETRIEVER,
    )
    context.event_timeline.append(
        event_type="workflow_completed",
        workflow_name="companion_interaction",
        request_id=request_id,
        correlation_id=correlation_id,
        user_id=str(session["user_id"]),
        payload={"risk_level": result.engagement.risk_level, "recommended_mode": result.engagement.recommended_mode},
    )
    return CompanionInteractionResponse(
        interaction=CompanionInteractionInfoResponse.model_validate(interaction.model_dump(mode="json")),
        snapshot=CompanionSnapshotResponse.model_validate(result.snapshot.model_dump(mode="json")),
        engagement=CompanionEngagementResponse.model_validate(result.engagement.model_dump(mode="json")),
        care_plan=CompanionCarePlanResponse.model_validate(result.care_plan.model_dump(mode="json")),
        clinician_digest_preview=ClinicianDigestResponse.model_validate(result.clinician_digest_preview.model_dump(mode="json")),
        impact=ImpactSummaryPayloadResponse.model_validate(result.impact.model_dump(mode="json")),
        workflow=build_workflow_response(context=context, correlation_id=correlation_id, request_id=request_id),
    )


def get_clinician_digest(*, context: AppContext, session: dict[str, object]) -> ClinicianDigestEnvelopeResponse:
    """Build the clinician-digest projection for the active session."""
    from dietary_guardian.application.companion.context import load_companion_inputs
    inputs = load_companion_inputs(context=context, session=session)
    _, _, _, digest, _, _ = build_companion_today_bundle(inputs=inputs, evidence_retriever=_EVIDENCE_RETRIEVER)
    return ClinicianDigestEnvelopeResponse(
        digest=ClinicianDigestResponse.model_validate(digest.model_dump(mode="json"))
    )


def get_impact_summary(*, context: AppContext, session: dict[str, object]) -> ImpactSummaryResponse:
    """Build the impact-summary projection for the active session."""
    from dietary_guardian.application.companion.context import load_companion_inputs
    inputs = load_companion_inputs(context=context, session=session)
    _, _, _, _, impact, _ = build_companion_today_bundle(inputs=inputs, evidence_retriever=_EVIDENCE_RETRIEVER)
    return ImpactSummaryResponse(
        summary=ImpactSummaryPayloadResponse.model_validate(impact.model_dump(mode="json"))
    )
