"""Module for test api typed contracts."""

from care_pilot.core.contracts.agent_envelopes import AgentOutputEnvelope
from care_pilot.core.contracts.api import (
    AlertTimelineItemResponse,
    AlertTimelineResponse,
    AlertTriggerResponse,
    ClinicalCardProvenanceResponse,
    ClinicalCardResponse,
    ClinicalCardTrendResponse,
    CursorPageResponse,
    MealAnalyzeResponse,
    MealRecordsResponse,
    RecommendationGenerateResponse,
    RecommendationInteractionItemResponse,
    RecommendationInteractionResponse,
    RecommendationPreferenceSnapshotResponse,
    ReminderConfirmResponse,
    ReminderGenerateResponse,
    ReminderListResponse,
    SuggestionItemResponse,
    SuggestionReportParseResponse,
    WorkflowResponse,
    WorkflowTimelineEventPayloadResponse,
    WorkflowTimelineEventResponse,
)
from care_pilot.features.companion.core.health.analytics import EngagementMetrics
from care_pilot.features.meals.domain.models import (
    NutritionRiskProfile,
    RawObservationBundle,
    ValidatedMealEvent,
)
from care_pilot.features.recommendations.domain import RecommendationOutput
from care_pilot.features.reminders.domain import ReminderEvent


def test_meal_contract_responses_use_typed_models() -> None:
    assert MealAnalyzeResponse.model_fields["raw_observation"].annotation is RawObservationBundle
    assert MealAnalyzeResponse.model_fields["nutrition_profile"].annotation is NutritionRiskProfile
    assert (
        MealAnalyzeResponse.model_fields["output_envelope"].annotation == AgentOutputEnvelope | None
    )
    assert MealAnalyzeResponse.model_fields["workflow"].annotation is WorkflowResponse
    assert MealRecordsResponse.model_fields["records"].annotation == list[ValidatedMealEvent]
    assert MealRecordsResponse.model_fields["page"].annotation == CursorPageResponse | None


def test_recommendation_and_suggestion_contracts_use_typed_models() -> None:
    assert (
        RecommendationGenerateResponse.model_fields["recommendation"].annotation
        is RecommendationOutput
    )
    assert RecommendationGenerateResponse.model_fields["workflow"].annotation is WorkflowResponse
    assert (
        SuggestionItemResponse.model_fields["report_parse"].annotation
        is SuggestionReportParseResponse
    )
    assert SuggestionItemResponse.model_fields["recommendation"].annotation is RecommendationOutput
    assert SuggestionItemResponse.model_fields["workflow"].annotation is WorkflowResponse


def test_reminder_contracts_use_typed_models() -> None:
    assert ReminderGenerateResponse.model_fields["reminders"].annotation == list[ReminderEvent]
    assert ReminderGenerateResponse.model_fields["metrics"].annotation is EngagementMetrics
    assert ReminderListResponse.model_fields["reminders"].annotation == list[ReminderEvent]
    assert ReminderListResponse.model_fields["metrics"].annotation is EngagementMetrics
    assert ReminderConfirmResponse.model_fields["event"].annotation is ReminderEvent
    assert ReminderConfirmResponse.model_fields["metrics"].annotation is EngagementMetrics


def test_alert_workflow_and_interaction_contracts_use_typed_models() -> None:
    assert (
        AlertTriggerResponse.model_fields["outbox_timeline"].annotation
        == list[AlertTimelineItemResponse]
    )
    assert AlertTriggerResponse.model_fields["workflow"].annotation is WorkflowResponse
    assert (
        AlertTimelineResponse.model_fields["outbox_timeline"].annotation
        == list[AlertTimelineItemResponse]
    )
    assert (
        WorkflowTimelineEventResponse.model_fields["payload"].annotation
        is WorkflowTimelineEventPayloadResponse
    )
    assert (
        RecommendationInteractionResponse.model_fields["interaction"].annotation
        is RecommendationInteractionItemResponse
    )
    assert (
        RecommendationInteractionResponse.model_fields["preference_snapshot"].annotation
        is RecommendationPreferenceSnapshotResponse
    )


def test_clinical_card_contracts_use_typed_models() -> None:
    assert (
        ClinicalCardResponse.model_fields["trends"].annotation
        == dict[str, ClinicalCardTrendResponse]
    )
    assert (
        ClinicalCardResponse.model_fields["provenance"].annotation is ClinicalCardProvenanceResponse
    )
