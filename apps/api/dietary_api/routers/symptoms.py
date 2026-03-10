"""API router for symptoms endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from ..routes_shared import current_session, get_context, require_action
from ..schemas import (
    SymptomCheckInEnvelopeResponse,
    SymptomCheckInListResponse,
    SymptomCheckInRequest,
    SymptomSummaryResponse,
)
from ..services.symptoms import (
    create_checkin_for_session,
    list_checkins_for_session,
    summarize_checkins_for_session,
)

router = APIRouter(tags=["symptoms"])


@router.post("/api/v1/symptoms/check-ins", response_model=SymptomCheckInEnvelopeResponse)
def symptoms_checkins_create(
    payload: SymptomCheckInRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> SymptomCheckInEnvelopeResponse:
    require_action(session, "symptoms.write")
    return create_checkin_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        payload=payload,
    )


@router.get("/api/v1/symptoms/check-ins", response_model=SymptomCheckInListResponse)
def symptoms_checkins_list(
    request: Request,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=50, ge=1, le=500),
    session: dict[str, object] = Depends(current_session),
) -> SymptomCheckInListResponse:
    require_action(session, "symptoms.read")
    return list_checkins_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )


@router.get("/api/v1/symptoms/summary", response_model=SymptomSummaryResponse)
def symptoms_summary(
    request: Request,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    session: dict[str, object] = Depends(current_session),
) -> SymptomSummaryResponse:
    require_action(session, "symptoms.read")
    return summarize_checkins_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        from_date=from_date,
        to_date=to_date,
    )
