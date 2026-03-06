from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from ..routes_shared import current_session, get_context, require_action
from ..schemas import (
    ClinicalCardEnvelopeResponse,
    ClinicalCardGenerateRequest,
    ClinicalCardListResponse,
)
from ..services.clinical_cards import (
    generate_clinical_card_for_session,
    get_clinical_card_for_session,
    list_clinical_cards_for_session,
)

router = APIRouter(tags=["clinical-cards"])


@router.post("/api/v1/clinical-cards/generate", response_model=ClinicalCardEnvelopeResponse)
def clinical_cards_generate(
    payload: ClinicalCardGenerateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ClinicalCardEnvelopeResponse:
    require_action(session, "clinical_cards.generate")
    return generate_clinical_card_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        payload=payload,
    )


@router.get("/api/v1/clinical-cards", response_model=ClinicalCardListResponse)
def clinical_cards_list(
    request: Request,
    limit: int = Query(default=20, ge=1, le=200),
    session: dict[str, object] = Depends(current_session),
) -> ClinicalCardListResponse:
    require_action(session, "clinical_cards.read")
    return list_clinical_cards_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        limit=limit,
    )


@router.get("/api/v1/clinical-cards/{card_id}", response_model=ClinicalCardEnvelopeResponse)
def clinical_cards_get(
    card_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> ClinicalCardEnvelopeResponse:
    require_action(session, "clinical_cards.read")
    return get_clinical_card_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        card_id=card_id,
    )
