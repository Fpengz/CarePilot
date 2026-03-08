from __future__ import annotations

from apps.api.dietary_api.auth import build_user_profile_from_session
from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import RecommendationGenerateResponse
from dietary_guardian.services.recommendation_service import generate_recommendation
from dietary_guardian.services.report_parser_service import build_clinical_snapshot


def generate_recommendation_for_session(
    *,
    context: AppContext,
    session: dict[str, object],
    request_id: str | None,
    correlation_id: str | None,
) -> RecommendationGenerateResponse:
    user_id = str(session["user_id"])
    meal_records = context.stores.meals.list_meal_records(user_id)
    if not meal_records:
        raise build_api_error(
            status_code=400,
            code="recommendations.no_meal_records",
            message="no meal records available",
        )

    snapshot = context.clinical_memory.get(user_id)
    if snapshot is None:
        readings = context.stores.biomarkers.list_biomarker_readings(user_id)
        if not readings:
            raise build_api_error(
                status_code=400,
                code="recommendations.no_clinical_snapshot",
                message="no clinical snapshot available",
            )
        snapshot = build_clinical_snapshot(readings)
        context.clinical_memory.put(user_id, snapshot)

    user_profile = build_user_profile_from_session(session, context.stores.profiles)
    recommendation = generate_recommendation(meal_records[-1], snapshot, user_profile)
    recommendation_json = recommendation.model_dump(mode="json")
    context.stores.recommendations.save_recommendation(user_id, recommendation_json)

    workflow = {
        "workflow_name": "recommendation_generate",
        "request_id": str(request_id or ""),
        "correlation_id": str(correlation_id or ""),
        "replayed": False,
        "timeline_events": [],
    }
    return RecommendationGenerateResponse(
        recommendation=recommendation_json,
        workflow=workflow,
    )
