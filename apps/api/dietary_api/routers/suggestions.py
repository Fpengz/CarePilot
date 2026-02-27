from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from dietary_guardian.services.recommendation_service import generate_recommendation
from dietary_guardian.services.report_parser_service import build_clinical_snapshot, parse_report_input
from dietary_guardian.models.report import ReportInput
from dietary_guardian.safety.triage import evaluate_text_safety

from ..auth import build_user_profile_from_session
from ..routes_shared import current_session, get_context, require_scopes
from ..schemas import (
    SuggestionDetailResponse,
    SuggestionGenerateFromReportRequest,
    SuggestionGenerateFromReportResponse,
    SuggestionItemResponse,
    SuggestionListResponse,
)

router = APIRouter(tags=["suggestions"])

SUGGESTION_DISCLAIMER = (
    "This information is for general wellness and care support only, not a diagnosis. "
    "If symptoms are severe, worsening, or concerning, seek urgent medical care."
)


def _build_workflow_stub() -> dict[str, object]:
    return {
        "workflow_name": "suggestions_generate_from_report",
        "request_id": str(uuid4()),
        "correlation_id": str(uuid4()),
        "replayed": False,
        "timeline_events": [],
    }


def _to_suggestion_response(payload: dict[str, object]) -> SuggestionItemResponse:
    return SuggestionItemResponse.model_validate(payload)


@router.post(
    "/api/v1/suggestions/generate-from-report",
    response_model=SuggestionGenerateFromReportResponse,
)
def suggestions_generate_from_report(
    payload: SuggestionGenerateFromReportRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> SuggestionGenerateFromReportResponse:
    require_scopes(session, {"report:write", "recommendation:generate"})
    context = get_context(request)
    user_id = str(session["user_id"])
    safety_decision = evaluate_text_safety(payload.text)

    created_at = datetime.now(timezone.utc)
    if safety_decision.decision != "allow":
        suggestion_payload: dict[str, object] = {
            "suggestion_id": str(uuid4()),
            "created_at": created_at.isoformat(),
            "disclaimer": SUGGESTION_DISCLAIMER,
            "safety": {
                "decision": safety_decision.decision,
                "reasons": safety_decision.reasons,
                "required_actions": safety_decision.required_actions,
                "redactions": safety_decision.redactions,
            },
            "report_parse": {"readings": [], "snapshot": {"biomarkers": {}, "risk_flags": []}},
            "recommendation": {
                "safe": False,
                "rationale": "Red-flag symptoms detected. Seek urgent medical care immediately.",
                "localized_advice": safety_decision.required_actions,
                "blocked_reason": "red_flag_escalation",
                "evidence": {},
            },
            "workflow": _build_workflow_stub(),
        }
        saved = context.repository.save_suggestion_record(user_id, suggestion_payload)
        return SuggestionGenerateFromReportResponse(suggestion=_to_suggestion_response(saved))

    meal_records = context.repository.list_meal_records(user_id)
    if not meal_records:
        raise HTTPException(status_code=400, detail="no meal records available")

    report_input = ReportInput(source="pasted_text", text=payload.text)
    readings = parse_report_input(report_input)
    snapshot = build_clinical_snapshot(readings)
    context.repository.save_biomarker_readings(user_id, readings)
    context.clinical_memory.put(user_id, snapshot)

    user_profile = build_user_profile_from_session(session)
    recommendation = generate_recommendation(meal_records[-1], snapshot, user_profile)
    recommendation_json = recommendation.model_dump(mode="json")
    context.repository.save_recommendation(user_id, recommendation_json)

    suggestion_payload: dict[str, object] = {
        "suggestion_id": str(uuid4()),
        "created_at": created_at.isoformat(),
        "disclaimer": SUGGESTION_DISCLAIMER,
        "safety": {
            "decision": safety_decision.decision,
            "reasons": safety_decision.reasons,
            "required_actions": safety_decision.required_actions,
            "redactions": safety_decision.redactions,
        },
        "report_parse": {
            "readings": [item.model_dump(mode="json") for item in readings],
            "snapshot": snapshot.model_dump(mode="json"),
        },
        "recommendation": recommendation_json,
        "workflow": _build_workflow_stub(),
    }
    saved = context.repository.save_suggestion_record(user_id, suggestion_payload)
    return SuggestionGenerateFromReportResponse(suggestion=_to_suggestion_response(saved))


@router.get("/api/v1/suggestions", response_model=SuggestionListResponse)
def suggestions_list(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    session: dict[str, object] = Depends(current_session),
) -> SuggestionListResponse:
    require_scopes(session, {"report:read"})
    context = get_context(request)
    user_id = str(session["user_id"])
    items = [
        _to_suggestion_response(item)
        for item in context.repository.list_suggestion_records(user_id, limit=limit)
    ]
    return SuggestionListResponse(items=items)


@router.get("/api/v1/suggestions/{suggestion_id}", response_model=SuggestionDetailResponse)
def suggestions_get(
    suggestion_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> SuggestionDetailResponse:
    require_scopes(session, {"report:read"})
    context = get_context(request)
    user_id = str(session["user_id"])
    item = context.repository.get_suggestion_record(user_id, suggestion_id)
    if item is None:
        raise HTTPException(status_code=404, detail="suggestion not found")
    return SuggestionDetailResponse(suggestion=_to_suggestion_response(item))
