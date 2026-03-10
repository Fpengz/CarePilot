"""API orchestration entry points for companion, clinician digest, and impact views."""

from __future__ import annotations

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
from apps.api.dietary_api.services.companion_context import (
    build_workflow_response,
    load_companion_inputs,
)
from dietary_guardian.application.companion import (
    build_companion_today_bundle,
)
from dietary_guardian.application.companion import (
    run_companion_interaction as orchestrate_companion_interaction,
)
from dietary_guardian.domain.companion import CompanionInteraction
from dietary_guardian.infrastructure.evidence import StaticEvidenceRetriever

_EVIDENCE_RETRIEVER = StaticEvidenceRetriever()


def get_companion_today(*, context: AppContext, session: dict[str, object]) -> CompanionTodayResponse:
    """Build the current companion summary for the active session."""
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



def run_companion_interaction(
    *,
    context: AppContext,
    session: dict[str, object],
    payload: CompanionInteractionRequest,
    request_id: str,
    correlation_id: str,
) -> CompanionInteractionResponse:
    """Run a single companion interaction and return the assembled care outputs."""
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
        workflow=build_workflow_response(context=context, correlation_id=correlation_id, request_id=request_id),
    )



def get_clinician_digest(*, context: AppContext, session: dict[str, object]) -> ClinicianDigestEnvelopeResponse:
    """Build the clinician-digest projection for the active session."""
    inputs = load_companion_inputs(context=context, session=session)
    _, _, _, digest, _, _ = build_companion_today_bundle(inputs=inputs, evidence_retriever=_EVIDENCE_RETRIEVER)
    return ClinicianDigestEnvelopeResponse(
        digest=ClinicianDigestResponse.model_validate(digest.model_dump(mode="json"))
    )



def get_impact_summary(*, context: AppContext, session: dict[str, object]) -> ImpactSummaryResponse:
    """Build the impact-summary projection for the active session."""
    inputs = load_companion_inputs(context=context, session=session)
    _, _, _, _, impact, _ = build_companion_today_bundle(inputs=inputs, evidence_retriever=_EVIDENCE_RETRIEVER)
    return ImpactSummaryResponse(
        summary=ImpactSummaryPayloadResponse.model_validate(impact.model_dump(mode="json"))
    )


__all__ = [
    "get_clinician_digest",
    "get_companion_today",
    "get_impact_summary",
    "run_companion_interaction",
]
