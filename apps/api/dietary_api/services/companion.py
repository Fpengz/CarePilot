from __future__ import annotations

from dietary_guardian.application.interactions import (
    CompanionStateInputs,
    build_companion_today_bundle,
    run_companion_interaction as orchestrate_companion_interaction,
)
from dietary_guardian.domain.care import CompanionInteraction
from dietary_guardian.infrastructure.evidence import StaticEvidenceRetriever
from dietary_guardian.models.report import ClinicalProfileSnapshot
from dietary_guardian.services.report_parser_service import build_clinical_snapshot

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
    WorkflowResponse,
    WorkflowTimelineEventResponse,
)
from apps.api.dietary_api.session_profiles import build_user_profile_from_session


_EVIDENCE_RETRIEVER = StaticEvidenceRetriever()


def _subject_user_id(session: dict[str, object]) -> str:
    raw = session.get("subject_user_id")
    if isinstance(raw, str) and raw.strip():
        return raw
    return str(session["user_id"])


def _clinical_snapshot(context: AppContext, *, user_id: str) -> ClinicalProfileSnapshot | None:
    cached = context.clinical_memory.get(user_id)
    if cached is not None:
        return cached
    readings = context.stores.biomarkers.list_biomarker_readings(user_id)
    if not readings:
        return None
    snapshot = build_clinical_snapshot(readings)
    context.clinical_memory.put(user_id, snapshot)
    return snapshot


def _emotion_signal(context: AppContext, *, emotion_text: str | None) -> str | None:
    if not emotion_text:
        return None
    try:
        result = context.emotion_service.infer_text(text=emotion_text)
    except Exception:
        lowered = emotion_text.lower()
        if any(term in lowered for term in ("stress", "stressed", "worried", "anxious")):
            return "anxious"
        if any(term in lowered for term in ("sad", "discouraged", "down", "frustrated")):
            return "sad"
        return None
    return str(result.emotion)


def _load_companion_inputs(
    *,
    context: AppContext,
    session: dict[str, object],
    emotion_text: str | None = None,
) -> CompanionStateInputs:
    subject_user_id = _subject_user_id(session)
    subject_session = dict(session)
    subject_session["user_id"] = subject_user_id
    user_profile = build_user_profile_from_session(subject_session, context.stores.profiles)
    health_profile = context.stores.profiles.get_health_profile(subject_user_id)
    meals = context.stores.meals.list_meal_records(subject_user_id)
    reminders = context.stores.reminders.list_reminder_events(subject_user_id)
    adherence_events = context.stores.medications.list_medication_adherence_events(user_id=subject_user_id)
    symptoms = context.stores.symptoms.list_symptom_checkins(user_id=subject_user_id, limit=200)
    readings = context.stores.biomarkers.list_biomarker_readings(subject_user_id)
    clinical_snapshot = _clinical_snapshot(context, user_id=subject_user_id)
    emotion_signal = _emotion_signal(context, emotion_text=emotion_text)
    return CompanionStateInputs(
        user_profile=user_profile,
        health_profile=health_profile,
        meals=meals,
        reminders=reminders,
        adherence_events=adherence_events,
        symptoms=symptoms,
        biomarker_readings=readings,
        clinical_snapshot=clinical_snapshot,
        emotion_signal=emotion_signal,
    )


def _workflow_response(*, context: AppContext, correlation_id: str, request_id: str) -> WorkflowResponse:
    timeline = context.event_timeline.list(correlation_id=correlation_id)
    return WorkflowResponse(
        workflow_name="companion_interaction",
        request_id=request_id,
        correlation_id=correlation_id,
        replayed=False,
        timeline_events=[
            WorkflowTimelineEventResponse.model_validate(item.model_dump(mode="json"))
            for item in timeline
        ],
    )


def get_companion_today(*, context: AppContext, session: dict[str, object]) -> CompanionTodayResponse:
    inputs = _load_companion_inputs(context=context, session=session)
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


def run_companion_interaction(
    *,
    context: AppContext,
    session: dict[str, object],
    payload: CompanionInteractionRequest,
    request_id: str,
    correlation_id: str,
) -> CompanionInteractionResponse:
    inputs = _load_companion_inputs(
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
    result = orchestrate_companion_interaction(
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
        workflow=_workflow_response(context=context, correlation_id=correlation_id, request_id=request_id),
    )


def get_clinician_digest(*, context: AppContext, session: dict[str, object]) -> ClinicianDigestEnvelopeResponse:
    inputs = _load_companion_inputs(context=context, session=session)
    _, _, _, digest, _, _ = build_companion_today_bundle(inputs=inputs, evidence_retriever=_EVIDENCE_RETRIEVER)
    return ClinicianDigestEnvelopeResponse(
        digest=ClinicianDigestResponse.model_validate(digest.model_dump(mode="json"))
    )


def get_impact_summary(*, context: AppContext, session: dict[str, object]) -> ImpactSummaryResponse:
    inputs = _load_companion_inputs(context=context, session=session)
    _, _, _, _, impact, _ = build_companion_today_bundle(inputs=inputs, evidence_retriever=_EVIDENCE_RETRIEVER)
    return ImpactSummaryResponse(
        summary=ImpactSummaryPayloadResponse.model_validate(impact.model_dump(mode="json"))
    )
