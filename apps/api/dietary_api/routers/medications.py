"""
Expose medication API endpoints.

This router defines medication regimen and adherence routes and delegates
to medication services for orchestration.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile

from ..routes_shared import current_session, get_context, require_action
from ..schemas import (
    MedicationAdherenceEventCreateRequest,
    MedicationAdherenceEventEnvelopeResponse,
    MedicationAdherenceMetricsResponse,
    MedicationDraftDeleteResponse,
    MedicationDraftInstructionUpdateRequest,
    MedicationIntakeConfirmRequest,
    MedicationIntakeResponse,
    MedicationIntakeTextRequest,
    MedicationRegimenCreateRequest,
    MedicationRegimenDeleteResponse,
    MedicationRegimenEnvelopeResponse,
    MedicationRegimenListResponse,
    MedicationRegimenPatchRequest,
)
from dietary_guardian.features.medications.use_cases import (
    adherence_metrics_for_session,
    cancel_intake_draft_for_session,
    confirm_intake_for_session,
    create_regimen_for_session,
    delete_regimen_for_session,
    delete_draft_instruction_for_session,
    intake_text_for_session,
    intake_upload_for_session,
    list_regimens_for_session,
    patch_regimen_for_session,
    update_draft_instruction_for_session,
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


@router.post("/api/v1/medications/intake/text", response_model=MedicationIntakeResponse)
async def medications_intake_text(
    payload: MedicationIntakeTextRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> MedicationIntakeResponse:
    require_action(session, "medications.regimens.write")
    return await intake_text_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        payload=payload,
        request_id=getattr(request.state, "request_id", None),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/api/v1/medications/intake/upload", response_model=MedicationIntakeResponse)
async def medications_intake_upload(
    request: Request,
    file: UploadFile = File(...),
    allow_ambiguous: bool = Form(default=False),
    session: dict[str, object] = Depends(current_session),
) -> MedicationIntakeResponse:
    require_action(session, "medications.regimens.write")
    content = await file.read()
    return await intake_upload_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        content=content,
        allow_ambiguous=allow_ambiguous,
        request_id=getattr(request.state, "request_id", None),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/api/v1/medications/intake/confirm", response_model=MedicationIntakeResponse)
def medications_intake_confirm(
    payload: MedicationIntakeConfirmRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> MedicationIntakeResponse:
    require_action(session, "medications.regimens.write")
    return confirm_intake_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        payload=payload,
    )


@router.patch("/api/v1/medications/intake/drafts/{draft_id}/instructions/{instruction_index}", response_model=MedicationIntakeResponse)
def medications_intake_draft_instruction_patch(
    draft_id: str,
    instruction_index: int,
    payload: MedicationDraftInstructionUpdateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> MedicationIntakeResponse:
    require_action(session, "medications.regimens.write")
    return update_draft_instruction_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        draft_id=draft_id,
        instruction_index=instruction_index,
        payload=payload,
    )


@router.delete("/api/v1/medications/intake/drafts/{draft_id}/instructions/{instruction_index}", response_model=MedicationIntakeResponse)
def medications_intake_draft_instruction_delete(
    draft_id: str,
    instruction_index: int,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> MedicationIntakeResponse:
    require_action(session, "medications.regimens.write")
    return delete_draft_instruction_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        draft_id=draft_id,
        instruction_index=instruction_index,
    )


@router.delete("/api/v1/medications/intake/drafts/{draft_id}", response_model=MedicationDraftDeleteResponse)
def medications_intake_draft_delete(
    draft_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> MedicationDraftDeleteResponse:
    require_action(session, "medications.regimens.write")
    return cancel_intake_draft_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        draft_id=draft_id,
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
