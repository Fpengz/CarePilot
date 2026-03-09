from uuid import uuid4

from fastapi import APIRouter, Depends, Request

from ..routes_shared import current_session, get_context, require_action
from ..schemas import (
    ClinicianDigestEnvelopeResponse,
    CompanionInteractionRequest,
    CompanionInteractionResponse,
    CompanionTodayResponse,
    ImpactSummaryResponse,
)
from ..services.companion import (
    get_clinician_digest,
    get_companion_today,
    get_impact_summary,
    run_companion_interaction,
)

router = APIRouter(tags=["companion"])


@router.get("/api/v1/companion/today", response_model=CompanionTodayResponse)
def companion_today(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> CompanionTodayResponse:
    require_action(session, "companion.today.read")
    return get_companion_today(context=get_context(request), session=session)


@router.post("/api/v1/companion/interactions", response_model=CompanionInteractionResponse)
def companion_interactions(
    payload: CompanionInteractionRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> CompanionInteractionResponse:
    require_action(session, "companion.interactions.write")
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    correlation_id = getattr(request.state, "correlation_id", None) or str(uuid4())
    return run_companion_interaction(
        context=get_context(request),
        session=session,
        payload=payload,
        request_id=request_id,
        correlation_id=correlation_id,
    )


@router.get("/api/v1/clinician/digest", response_model=ClinicianDigestEnvelopeResponse)
def clinician_digest(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ClinicianDigestEnvelopeResponse:
    require_action(session, "clinician.digest.read")
    return get_clinician_digest(context=get_context(request), session=session)


@router.get("/api/v1/impact/summary", response_model=ImpactSummaryResponse)
def impact_summary(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ImpactSummaryResponse:
    require_action(session, "impact.summary.read")
    return get_impact_summary(context=get_context(request), session=session)
