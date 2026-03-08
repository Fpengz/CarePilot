from typing import get_type_hints

from apps.api.dietary_api import deps
from apps.api.dietary_api.services import emotions, meals, recommendations, workflows


def test_domain_dependency_provider_types_exist() -> None:
    assert hasattr(deps, "MealDeps")
    assert hasattr(deps, "RecommendationDeps")
    assert hasattr(deps, "WorkflowDeps")
    assert hasattr(deps, "EmotionDeps")


def test_target_services_depend_on_scoped_providers() -> None:
    assert get_type_hints(meals.analyze_meal)["deps"] is deps.MealDeps
    assert get_type_hints(recommendations.generate_recommendation_for_session)["deps"] is deps.RecommendationDeps
    assert get_type_hints(workflows.get_workflow)["deps"] is deps.WorkflowDeps
    assert get_type_hints(emotions.infer_text_for_session)["deps"] is deps.EmotionDeps
