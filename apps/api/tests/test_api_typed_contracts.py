"""Module for test api typed contracts."""

from apps.api.dietary_api.schemas import (
    AlertTimelineItemResponse,
    AlertTimelineResponse,
    AlertTriggerResponse,
    ClinicalCardProvenanceResponse,
    ClinicalCardResponse,
    ClinicalCardTrendResponse,
    CursorPageResponse,
    MealAnalyzeResponse,
    MealAnalyzeSummaryResponse,
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

from dietary_guardian.domain.notifications.models import ReminderEvent
from dietary_guardian.domain.recommendations.models import RecommendationOutput
from dietary_guardian.models.analytics import EngagementMetrics
from dietary_guardian.models.contracts import AgentOutputEnvelope
from dietary_guardian.models.meal import VisionResult
from dietary_guardian.models.meal_record import MealRecognitionRecord


def test_meal_contract_responses_use_typed_models() -> None:
    assert MealAnalyzeResponse.model_fields["summary"].annotation is MealAnalyzeSummaryResponse
    assert MealAnalyzeResponse.model_fields["vision_result"].annotation is VisionResult
    assert MealAnalyzeResponse.model_fields["meal_record"].annotation is MealRecognitionRecord
    assert MealAnalyzeResponse.model_fields["output_envelope"].annotation == AgentOutputEnvelope | None
    assert MealAnalyzeResponse.model_fields["workflow"].annotation is WorkflowResponse
    assert MealRecordsResponse.model_fields["records"].annotation == list[MealRecognitionRecord]
    assert MealRecordsResponse.model_fields["page"].annotation == CursorPageResponse | None


def test_recommendation_and_suggestion_contracts_use_typed_models() -> None:
    assert RecommendationGenerateResponse.model_fields["recommendation"].annotation is RecommendationOutput
    assert RecommendationGenerateResponse.model_fields["workflow"].annotation is WorkflowResponse
    assert SuggestionItemResponse.model_fields["report_parse"].annotation is SuggestionReportParseResponse
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
    assert AlertTriggerResponse.model_fields["outbox_timeline"].annotation == list[AlertTimelineItemResponse]
    assert AlertTriggerResponse.model_fields["workflow"].annotation is WorkflowResponse
    assert AlertTimelineResponse.model_fields["outbox_timeline"].annotation == list[AlertTimelineItemResponse]
    assert WorkflowTimelineEventResponse.model_fields["payload"].annotation is WorkflowTimelineEventPayloadResponse
    assert RecommendationInteractionResponse.model_fields["interaction"].annotation is RecommendationInteractionItemResponse
    assert (
        RecommendationInteractionResponse.model_fields["preference_snapshot"].annotation
        is RecommendationPreferenceSnapshotResponse
    )


def test_clinical_card_contracts_use_typed_models() -> None:
    assert ClinicalCardResponse.model_fields["trends"].annotation == dict[str, ClinicalCardTrendResponse]
    assert ClinicalCardResponse.model_fields["provenance"].annotation is ClinicalCardProvenanceResponse
