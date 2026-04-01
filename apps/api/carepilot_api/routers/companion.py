"""
Expose companion care-loop API endpoints.

This router defines companion-facing routes for daily guidance, interactions,
and clinician views, delegating orchestration to API services.
"""

from datetime import date
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request  # Import Query

from ..routes_shared import current_session, get_context, require_action
from ..schemas import (
    BloodPressureChartResponse,
    BloodPressureSummaryEnvelopeResponse,
    ClinicianDigestEnvelopeResponse,
    CompanionInteractionRequest,
    CompanionInteractionResponse,
    CompanionTodayResponse,
    ImpactSummaryResponse,
    PatientMedicalCardResponse,
)
from ..services.companion_service import (
    get_blood_pressure_chart,
    get_blood_pressure_summary,
    get_clinician_digest,
    get_companion_today,
    get_impact_summary,
    handle_companion_interaction,
)
from ..services.patient_card import generate_patient_medical_card_for_session

router = APIRouter(tags=["companion"])


@router.get("/api/v1/companion/today", response_model=CompanionTodayResponse)
async def companion_today(
    request: Request,
    include: str | None = Query(None),  # Added include parameter
    session: dict[str, object] = Depends(current_session),
) -> CompanionTodayResponse:
    require_action(session, "companion.today.read")
    return await get_companion_today(
        context=get_context(request), session=session, include=include
    )  # Pass include parameter to service


@router.get(
    "/api/v1/companion/blood-pressure",
    response_model=BloodPressureSummaryEnvelopeResponse,
)
async def companion_blood_pressure_summary(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> BloodPressureSummaryEnvelopeResponse:
    require_action(session, "companion.today.read")
    return await get_blood_pressure_summary(context=get_context(request), session=session)


@router.get(
    "/api/v1/companion/blood-pressure-chart",
    response_model=BloodPressureChartResponse,
)
async def companion_blood_pressure_chart(
    request: Request,
    range: str = Query(default="30d"),
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    session: dict[str, object] = Depends(current_session),
) -> BloodPressureChartResponse:
    require_action(session, "companion.today.read")
    parsed_from = date.fromisoformat(from_date) if from_date else None
    parsed_to = date.fromisoformat(to_date) if to_date else None
    try:
        return await get_blood_pressure_chart(
            context=get_context(request),
            session=session,
            range_key=range,
            from_date=parsed_from,
            to_date=parsed_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/v1/companion/interactions", response_model=CompanionInteractionResponse)
async def companion_interactions(
    payload: CompanionInteractionRequest,
    request: Request,
    include: str | None = Query(None),  # Added include parameter
    session: dict[str, object] = Depends(current_session),
) -> CompanionInteractionResponse:
    require_action(session, "companion.interactions.write")
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    correlation_id = getattr(request.state, "correlation_id", None) or str(uuid4())
    return await handle_companion_interaction(
        context=get_context(request),
        session=session,
        payload=payload,
        request_id=request_id,
        correlation_id=correlation_id,
        include=include,  # Pass include parameter to service
    )


@router.get("/api/v1/clinician/digest", response_model=ClinicianDigestEnvelopeResponse)
async def clinician_digest(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ClinicianDigestEnvelopeResponse:
    require_action(session, "clinician.digest.read")
    return await get_clinician_digest(context=get_context(request), session=session)


@router.get("/api/v1/impact/summary", response_model=ImpactSummaryResponse)
async def impact_summary(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ImpactSummaryResponse:
    require_action(session, "impact.summary.read")
    return await get_impact_summary(context=get_context(request), session=session)


@router.get(
    "/api/v1/companion/patient-card",
    response_model=PatientMedicalCardResponse,
)
async def patient_medical_card(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> PatientMedicalCardResponse:
    require_action(session, "companion.patient_card.read")
    return await generate_patient_medical_card_for_session(
        context=get_context(request), session=session
    )
