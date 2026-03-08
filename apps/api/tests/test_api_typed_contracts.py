from apps.api.dietary_api.schemas.models import (
    CursorPageResponse,
    MealAnalyzeResponse,
    MealAnalyzeSummaryResponse,
    MealRecordsResponse,
    RecommendationGenerateResponse,
    ReminderConfirmResponse,
    ReminderGenerateResponse,
    ReminderListResponse,
    SuggestionReportParseResponse,
    SuggestionItemResponse,
    WorkflowResponse,
)
from dietary_guardian.models.analytics import EngagementMetrics
from dietary_guardian.models.contracts import AgentOutputEnvelope
from dietary_guardian.models.meal import VisionResult
from dietary_guardian.models.meal_record import MealRecognitionRecord
from dietary_guardian.models.medication import ReminderEvent
from dietary_guardian.models.recommendation import RecommendationOutput


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
