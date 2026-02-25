from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from dietary_guardian.services.recommendation_service import generate_recommendation
from dietary_guardian.services.report_parser_service import build_clinical_snapshot

from ..auth import build_user_profile_from_session
from ..routes_shared import current_session, get_context, require_scopes
from ..schemas import RecommendationGenerateResponse

router = APIRouter(tags=["recommendations"])


@router.post("/api/v1/recommendations/generate", response_model=RecommendationGenerateResponse)
def recommendations_generate(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> RecommendationGenerateResponse:
    require_scopes(session, {"recommendation:generate"})
    context = get_context(request)
    user_id = str(session["user_id"])
    meal_records = context.repository.list_meal_records(user_id)
    if not meal_records:
        raise HTTPException(status_code=400, detail="no meal records available")
    snapshot = context.clinical_memory.get(user_id)
    if snapshot is None:
        readings = context.repository.list_biomarker_readings(user_id)
        if not readings:
            raise HTTPException(status_code=400, detail="no clinical snapshot available")
        snapshot = build_clinical_snapshot(readings)
        context.clinical_memory.put(user_id, snapshot)
    user_profile = build_user_profile_from_session(session)
    recommendation = generate_recommendation(meal_records[-1], snapshot, user_profile)
    context.repository.save_recommendation(user_id, recommendation.model_dump(mode="json"))
    workflow = {
        "workflow_name": "recommendation_generate",
        "request_id": str(uuid4()),
        "correlation_id": str(uuid4()),
        "replayed": False,
        "timeline_events": [],
    }
    return RecommendationGenerateResponse(
        recommendation=recommendation.model_dump(mode="json"),
        workflow=workflow,
    )
