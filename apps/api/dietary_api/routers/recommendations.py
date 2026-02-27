from fastapi import APIRouter, Depends, Request
from ..routes_shared import current_session, get_context, require_action
from ..schemas import RecommendationGenerateResponse
from ..services.recommendations import generate_recommendation_for_session

router = APIRouter(tags=["recommendations"])


@router.post("/api/v1/recommendations/generate", response_model=RecommendationGenerateResponse)
def recommendations_generate(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> RecommendationGenerateResponse:
    require_action(session, "recommendations.generate")
    return generate_recommendation_for_session(
        context=get_context(request),
        session=session,
        request_id=getattr(request.state, "request_id", None),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
