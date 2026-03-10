"""API router for medications endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from ..routes_shared import current_session, get_context, require_action
from ..schemas import (
    MedicationAdherenceEventCreateRequest,
    MedicationAdherenceEventEnvelopeResponse,
    MedicationAdherenceMetricsResponse,
    MedicationRegimenCreateRequest,
    MedicationRegimenDeleteResponse,
    MedicationRegimenEnvelopeResponse,
    MedicationRegimenListResponse,
    MedicationRegimenPatchRequest,
)
from ..services.medications import (
    adherence_metrics_for_session,
    create_regimen_for_session,
    delete_regimen_for_session,
    list_regimens_for_session,
    patch_regimen_for_session,
    record_adherence_for_session,
)

router = APIRouter(tags=["medications"])


@router.get("/api/v1/medications/regimens", response_model=MedicationRegimenListResponse)
def medications_regimens_list(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> MedicationRegimenListResponse:
    require_action(session, "medications.regimens.read")
    return list_regimens_for_session(context=get_context(request), user_id=str(session["user_id"]))


@router.post("/api/v1/medications/regimens", response_model=MedicationRegimenEnvelopeResponse)
def medications_regimens_create(
    payload: MedicationRegimenCreateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> MedicationRegimenEnvelopeResponse:
    require_action(session, "medications.regimens.write")
    return create_regimen_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        payload=payload,
    )


@router.patch("/api/v1/medications/regimens/{regimen_id}", response_model=MedicationRegimenEnvelopeResponse)
def medications_regimens_patch(
    regimen_id: str,
    payload: MedicationRegimenPatchRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> MedicationRegimenEnvelopeResponse:
    require_action(session, "medications.regimens.write")
    return patch_regimen_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        regimen_id=regimen_id,
        payload=payload,
    )


@router.delete("/api/v1/medications/regimens/{regimen_id}", response_model=MedicationRegimenDeleteResponse)
def medications_regimens_delete(
    regimen_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> MedicationRegimenDeleteResponse:
    require_action(session, "medications.regimens.write")
    return delete_regimen_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        regimen_id=regimen_id,
    )


@router.post("/api/v1/medications/adherence-events", response_model=MedicationAdherenceEventEnvelopeResponse)
def medications_adherence_create(
    payload: MedicationAdherenceEventCreateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> MedicationAdherenceEventEnvelopeResponse:
    require_action(session, "medications.adherence.write")
    return record_adherence_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        payload=payload,
    )


@router.get("/api/v1/medications/adherence-metrics", response_model=MedicationAdherenceMetricsResponse)
def medications_adherence_metrics(
    request: Request,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    session: dict[str, object] = Depends(current_session),
) -> MedicationAdherenceMetricsResponse:
    require_action(session, "medications.adherence.read")
    return adherence_metrics_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        from_date=from_date,
        to_date=to_date,
    )
