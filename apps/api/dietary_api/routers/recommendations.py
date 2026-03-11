"""API router for recommendations endpoints."""

from fastapi import APIRouter, Depends, Request

from ..deps import recommendation_agent_deps, recommendation_deps
from ..routes_shared import current_session, get_context, require_action
from ..schemas import (
    RecommendationAgentResponse,
    RecommendationGenerateResponse,
    RecommendationInteractionRequest,
    RecommendationInteractionResponse,
    RecommendationSubstitutionRequest,
    RecommendationSubstitutionResponse,
)
from dietary_guardian.application.recommendations.use_cases import (
    generate_recommendation_for_session,
    get_daily_agent_for_session,
    get_substitutions_for_session,
    record_interaction_for_session,
)

router = APIRouter(tags=["recommendations"])


@router.post("/api/v1/recommendations/generate", response_model=RecommendationGenerateResponse)
def recommendations_generate(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> RecommendationGenerateResponse:
    require_action(session, "recommendations.generate")
    return generate_recommendation_for_session(
        deps=recommendation_deps(get_context(request)),
        session=session,
        request_id=getattr(request.state, "request_id", None),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/api/v1/recommendations/daily-agent", response_model=RecommendationAgentResponse)
def recommendations_daily_agent(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> RecommendationAgentResponse:
    require_action(session, "recommendations.daily_agent.read")
    return get_daily_agent_for_session(
        deps=recommendation_agent_deps(get_context(request)),
        session=session,
        request_id=getattr(request.state, "request_id", None),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/api/v1/recommendations/substitutions", response_model=RecommendationSubstitutionResponse)
def recommendations_substitutions(
    payload: RecommendationSubstitutionRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> RecommendationSubstitutionResponse:
    require_action(session, "recommendations.substitutions.generate")
    return get_substitutions_for_session(
        deps=recommendation_agent_deps(get_context(request)),
        session=session,
        payload=payload,
    )


@router.post("/api/v1/recommendations/interactions", response_model=RecommendationInteractionResponse)
def recommendations_interactions(
    payload: RecommendationInteractionRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> RecommendationInteractionResponse:
    require_action(session, "recommendations.interactions.write")
    return record_interaction_for_session(
        deps=recommendation_agent_deps(get_context(request)),
        session=session,
        payload=payload,
    )
