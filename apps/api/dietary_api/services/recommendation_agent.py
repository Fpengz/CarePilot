from __future__ import annotations

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    RecommendationAgentResponse,
    RecommendationInteractionRequest,
    RecommendationInteractionResponse,
    RecommendationSubstitutionRequest,
    RecommendationSubstitutionResponse,
)
from dietary_guardian.services.health_profile_service import resolve_user_profile
from dietary_guardian.services.recommendation_agent_service import (
    AgentMealNotFoundError,
    build_substitution_plan,
    generate_daily_agent_recommendation,
    record_interaction_and_update_preferences,
)
from dietary_guardian.services.report_parser_service import build_clinical_snapshot


def _resolve_clinical_snapshot(*, context: AppContext, user_id: str):
    snapshot = context.clinical_memory.get(user_id)
    if snapshot is not None:
        return snapshot
    readings = context.stores.biomarkers.list_biomarker_readings(user_id)
    if not readings:
        return None
    snapshot = build_clinical_snapshot(readings)
    context.clinical_memory.put(user_id, snapshot)
    return snapshot


def get_daily_agent_for_session(
    *,
    context: AppContext,
    session: dict[str, object],
    request_id: str | None,
    correlation_id: str | None,
) -> RecommendationAgentResponse:
    user_id = str(session["user_id"])
    health_profile, user_profile = resolve_user_profile(context.repository, session)
    meal_history = context.stores.meals.list_meal_records(user_id)
    clinical_snapshot = _resolve_clinical_snapshot(context=context, user_id=user_id)
    recommendation = generate_daily_agent_recommendation(
        repository=context.repository,
        user_id=user_id,
        health_profile=health_profile,
        user_profile=user_profile,
        meal_history=meal_history,
        clinical_snapshot=clinical_snapshot,
    )
    payload = recommendation.model_dump(mode="json")
    payload["workflow"] = {
        "workflow_name": "daily_recommendation_agent",
        "request_id": str(request_id or ""),
        "correlation_id": str(correlation_id or ""),
        "replayed": False,
        "timeline_events": [],
    }
    return RecommendationAgentResponse.model_validate(payload)


def get_substitutions_for_session(
    *,
    context: AppContext,
    session: dict[str, object],
    payload: RecommendationSubstitutionRequest,
) -> RecommendationSubstitutionResponse:
    user_id = str(session["user_id"])
    health_profile, user_profile = resolve_user_profile(context.repository, session)
    meal_history = context.stores.meals.list_meal_records(user_id)
    clinical_snapshot = _resolve_clinical_snapshot(context=context, user_id=user_id)
    try:
        plan = build_substitution_plan(
            repository=context.repository,
            user_id=user_id,
            health_profile=health_profile,
            user_profile=user_profile,
            meal_history=meal_history,
            clinical_snapshot=clinical_snapshot,
            source_meal_id=payload.source_meal_id,
            limit=payload.limit,
        )
    except AgentMealNotFoundError as exc:
        raise build_api_error(
            status_code=404,
            code="recommendations.meal_not_found",
            message="meal record not found",
            details={"meal_id": str(exc)},
        ) from exc
    if plan is None:
        raise build_api_error(
            status_code=400,
            code="recommendations.no_meal_records",
            message="no meal records available",
        )
    return RecommendationSubstitutionResponse.model_validate(plan.model_dump(mode="json"))


def record_interaction_for_session(
    *,
    context: AppContext,
    session: dict[str, object],
    payload: RecommendationInteractionRequest,
) -> RecommendationInteractionResponse:
    user_id = str(session["user_id"])
    meal_history = context.stores.meals.list_meal_records(user_id)
    try:
        interaction, snapshot = record_interaction_and_update_preferences(
            repository=context.repository,
            user_id=user_id,
            candidate_id=payload.candidate_id,
            recommendation_id=payload.recommendation_id,
            event_type=payload.event_type,
            slot=payload.slot,
            source_meal_id=payload.source_meal_id,
            selected_meal_id=payload.selected_meal_id,
            metadata=payload.metadata,
            meal_history=meal_history,
        )
    except AgentMealNotFoundError as exc:
        raise build_api_error(
            status_code=404,
            code="recommendations.candidate_not_found",
            message="candidate not found",
            details={"candidate_id": str(exc)},
        ) from exc
    return RecommendationInteractionResponse(
        interaction=interaction.model_dump(mode="json"),
        preference_snapshot=snapshot.model_dump(mode="json"),
    )
