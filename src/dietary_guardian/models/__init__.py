"""Compatibility facade: most type definitions now live in dietary_guardian.domain subpackages."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from dietary_guardian.models.alerting import (
    AlertDeliveryResult,
    AlertMessage,
    AlertSeverity,
    OutboxRecord,
)
from dietary_guardian.models.health_profile import HealthProfileRecord
from dietary_guardian.models.medication_tracking import MedicationAdherenceEvent, MedicationAdherenceMetrics
from dietary_guardian.models.medication import MedicationRegimen
from dietary_guardian.models.metrics_trend import MetricPoint, MetricTrend
from dietary_guardian.models.report import BiomarkerReading, ClinicalProfileSnapshot, ReportInput
from dietary_guardian.models.symptom import SymptomCheckIn, SymptomSafety, SymptomSummary
from dietary_guardian.models.tool_policy import ToolRolePolicyRecord
from dietary_guardian.models.workflow_contract_snapshot import WorkflowContractSnapshotRecord
from dietary_guardian.models.analytics import EngagementMetrics
from dietary_guardian.models.clinical_card import ClinicalCardRecord
from dietary_guardian.models.daily_suggestions import DailySuggestionBundle, DailySuggestionItem
from dietary_guardian.models.emotion import (
    EmotionConfidenceBand,
    EmotionEvidence,
    EmotionInferenceResult,
    EmotionLabel,
    EmotionRuntimeHealth,
)
from dietary_guardian.models.health_profile import ProfileCompleteness
from dietary_guardian.models.inference import (
    InferenceHealth,
    InferenceModality,
    InferenceRequest,
    InferenceResponse,
    ProviderMetadata,
)
from dietary_guardian.models.identity import AccountPrincipal, AccountRole, PermissionScope, ProfileMode
from dietary_guardian.models.meal import (
    GlycemicIndexLevel,
    ImageInput,
    Ingredient,
    MealEvent,
    MealState,
    Nutrition,
    PortionSize,
    VisionResult,
)
from dietary_guardian.models.meal_record import MealRecognitionRecord
from dietary_guardian.models.medication import ReminderEvent
from dietary_guardian.models.recommendation_agent import (
    AgentProfileState,
    AgentRecommendationCard,
    CandidateScores,
    DailyAgentRecommendation,
    HealthDelta,
    MealCatalogItem,
    PreferenceSnapshot,
    RecommendationInteraction,
    SourceMealSummary,
    SubstitutionAlternative,
    SubstitutionPlan,
    TemporalContext,
)
from dietary_guardian.models.recommendation import RecommendationOutput
from dietary_guardian.models.profile_tools import (
    CaregiverToolState,
    ClinicalSummaryToolState,
    SelfToolState,
)
from dietary_guardian.models.role_tools import AgentRoleToolContract, RoleToolContract
from dietary_guardian.models.social import BlockScore, CommunityChallenge
from dietary_guardian.models.user import (
    MealScheduleWindow,
    MealSlot,
    MedicalCondition,
    Medication,
    UserProfile,
)

if TYPE_CHECKING:
    from dietary_guardian.domain.meals import (
        EnrichedMealEvent,
        MealNutritionProfile,
        MealPerception,
        MealPortionEstimate,
        NormalizedMealItem,
        PortionReference,
        RawFoodSourceRecord,
    )
    from dietary_guardian.models.canonical_food import (
        CanonicalFoodAdvice,
        CanonicalFoodAlternative,
        CanonicalFoodRecord,
    )

_LAZY_EXPORTS = {
    "CanonicalFoodAdvice": ("dietary_guardian.models.canonical_food", "CanonicalFoodAdvice"),
    "CanonicalFoodAlternative": ("dietary_guardian.models.canonical_food", "CanonicalFoodAlternative"),
    "CanonicalFoodRecord": ("dietary_guardian.models.canonical_food", "CanonicalFoodRecord"),
    "EnrichedMealEvent": ("dietary_guardian.domain.meals", "EnrichedMealEvent"),
    "MealNutritionProfile": ("dietary_guardian.domain.meals", "MealNutritionProfile"),
    "MealPerception": ("dietary_guardian.domain.meals", "MealPerception"),
    "MealPortionEstimate": ("dietary_guardian.domain.meals", "MealPortionEstimate"),
    "NormalizedMealItem": ("dietary_guardian.domain.meals", "NormalizedMealItem"),
    "PortionReference": ("dietary_guardian.domain.meals", "PortionReference"),
    "RawFoodSourceRecord": ("dietary_guardian.domain.meals", "RawFoodSourceRecord"),
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = _LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value

__all__ = [
    "GlycemicIndexLevel",
    "ImageInput",
    "Ingredient",
    "MealEvent",
    "MealState",
    "Nutrition",
    "PortionSize",
    "VisionResult",
    "MealRecognitionRecord",
    "MedicationRegimen",
    "ReminderEvent",
    "RecommendationOutput",
    "BiomarkerReading",
    "ClinicalProfileSnapshot",
    "ReportInput",
    "CaregiverToolState",
    "ClinicalSummaryToolState",
    "SelfToolState",
    "AgentRoleToolContract",
    "RoleToolContract",
    "ToolRolePolicyRecord",
    "BlockScore",
    "CommunityChallenge",
    "MealScheduleWindow",
    "MealSlot",
    "MedicalCondition",
    "Medication",
    "UserProfile",
    "AccountRole",
    "ProfileMode",
    "PermissionScope",
    "AccountPrincipal",
    "EngagementMetrics",
    "AlertMessage",
    "OutboxRecord",
    "AlertDeliveryResult",
    "AlertSeverity",
    "ClinicalCardRecord",
    "CanonicalFoodAdvice",
    "CanonicalFoodAlternative",
    "CanonicalFoodRecord",
    "DailySuggestionBundle",
    "DailySuggestionItem",
    "EmotionLabel",
    "EmotionConfidenceBand",
    "EmotionEvidence",
    "EmotionInferenceResult",
    "EmotionRuntimeHealth",
    "HealthProfileRecord",
    "ProfileCompleteness",
    "AgentProfileState",
    "AgentRecommendationCard",
    "CandidateScores",
    "DailyAgentRecommendation",
    "HealthDelta",
    "MealCatalogItem",
    "MedicationAdherenceEvent",
    "MedicationAdherenceMetrics",
    "MetricPoint",
    "MetricTrend",
    "PreferenceSnapshot",
    "RecommendationInteraction",
    "SourceMealSummary",
    "SubstitutionAlternative",
    "SubstitutionPlan",
    "SymptomCheckIn",
    "SymptomSafety",
    "SymptomSummary",
    "WorkflowContractSnapshotRecord",
    "TemporalContext",
    "InferenceModality",
    "ProviderMetadata",
    "InferenceRequest",
    "InferenceResponse",
    "InferenceHealth",
    "MealNutritionProfile",
    "MealPerception",
    "MealPortionEstimate",
    "NormalizedMealItem",
    "EnrichedMealEvent",
    "PortionReference",
    "RawFoodSourceRecord",
]
