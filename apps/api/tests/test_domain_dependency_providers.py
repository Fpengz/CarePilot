"""Module for test domain dependency providers."""

from typing import get_type_hints

from apps.api.dietary_api import deps
from apps.api.dietary_api.services import (
    alerts,
    clinical_cards,
    emotions,
    meals,
    recommendation_agent,
    recommendations,
    workflows,
)


def test_domain_dependency_provider_types_exist() -> None:
    assert hasattr(deps, "MealDeps")
    assert hasattr(deps, "RecommendationDeps")
    assert hasattr(deps, "RecommendationAgentDeps")
    assert hasattr(deps, "WorkflowDeps")
    assert hasattr(deps, "EmotionDeps")
    assert hasattr(deps, "AlertDeps")
    assert hasattr(deps, "ClinicalCardDeps")


def test_target_services_depend_on_scoped_providers() -> None:
    assert get_type_hints(meals.analyze_meal)["deps"] is deps.MealDeps
    assert get_type_hints(recommendations.generate_recommendation_for_session)["deps"] is deps.RecommendationDeps
    assert get_type_hints(recommendation_agent.get_daily_agent_for_session)["deps"] is deps.RecommendationAgentDeps
    assert get_type_hints(alerts.trigger_alert)["deps"] is deps.AlertDeps
    assert get_type_hints(clinical_cards.generate_clinical_card_for_session)["deps"] is deps.ClinicalCardDeps
    assert get_type_hints(workflows.get_workflow)["deps"] is deps.WorkflowDeps
    assert get_type_hints(emotions.infer_text_for_session)["deps"] is deps.EmotionDeps
