"""Module for test domain dependency providers."""

from typing import get_type_hints

from apps.api.carepilot_api import deps
from apps.api.carepilot_api.services import emotion_session, meals, workflows

from care_pilot.features.companion.clinician_digest.clinical_cards import clinical_card_service
from care_pilot.features.recommendations import recommendation_engine, recommendation_service
from care_pilot.features.reminders.notifications import alert_session


def test_domain_dependency_provider_types_exist() -> None:
    assert hasattr(deps, "MealDeps")
    assert hasattr(deps, "RecommendationDeps")
    assert hasattr(deps, "RecommendationAgentDeps")
    assert hasattr(deps, "WorkflowDeps")
    assert hasattr(deps, "EmotionDeps")
    assert hasattr(deps, "AlertDeps")
    assert hasattr(deps, "ClinicalCardDeps")


def test_target_services_depend_on_scoped_providers() -> None:
    # Use localns so that TYPE_CHECKING-only imports (e.g. WorkflowDeps used in
    # coordinator.py) can still be resolved by get_type_hints.
    from apps.api.carepilot_api import deps as _deps_module

    _ns = vars(_deps_module)

    assert get_type_hints(meals.analyze_meal, localns=_ns)["deps"] is deps.MealDeps
    assert (
        get_type_hints(recommendation_engine.generate_recommendation_for_session, localns=_ns)["deps"]
        is deps.RecommendationDeps
    )
    assert (
        get_type_hints(recommendation_service.get_daily_agent_for_session, localns=_ns)["deps"]
        is deps.RecommendationAgentDeps
    )
    assert get_type_hints(alert_session.trigger_alert_for_session, localns=_ns)["deps"] is deps.AlertDeps
    assert (
        get_type_hints(clinical_card_service.generate_clinical_card_for_session, localns=_ns)["deps"]
        is deps.ClinicalCardDeps
    )
    assert get_type_hints(workflows.get_workflow, localns=_ns)["deps"] is deps.WorkflowDeps
    assert (
        get_type_hints(emotion_session.infer_text_for_session, localns=_ns)["deps"]
        is deps.EmotionDeps
    )
