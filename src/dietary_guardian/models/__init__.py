"""Local model definitions that have not yet migrated to domain subpackages.

Domain types (alerts, health, identity, notifications, recommendations, workflows)
now live in their respective ``dietary_guardian.domain.*`` modules. Import from
those directly; this package only exposes types that are still canonical here.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from dietary_guardian.models.analytics import EngagementMetrics
from dietary_guardian.models.clinical_card import ClinicalCardRecord
from dietary_guardian.models.emotion import (
    EmotionConfidenceBand,
    EmotionEvidence,
    EmotionInferenceResult,
    EmotionLabel,
    EmotionRuntimeHealth,
)
from dietary_guardian.models.inference import (
    InferenceHealth,
    InferenceModality,
    InferenceRequest,
    InferenceResponse,
    ProviderMetadata,
)
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
from dietary_guardian.models.profile_tools import (
    CaregiverToolState,
    ClinicalSummaryToolState,
    SelfToolState,
)
from dietary_guardian.models.role_tools import AgentRoleToolContract, RoleToolContract
from dietary_guardian.models.social import BlockScore, CommunityChallenge

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
    from dietary_guardian.domain.recommendations.models import (
        CanonicalFoodAdvice,
        CanonicalFoodAlternative,
        CanonicalFoodRecord,
    )

_LAZY_EXPORTS = {
    "CanonicalFoodAdvice": ("dietary_guardian.domain.recommendations.models", "CanonicalFoodAdvice"),
    "CanonicalFoodAlternative": ("dietary_guardian.domain.recommendations.models", "CanonicalFoodAlternative"),
    "CanonicalFoodRecord": ("dietary_guardian.domain.recommendations.models", "CanonicalFoodRecord"),
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
    # meal models
    "GlycemicIndexLevel",
    "ImageInput",
    "Ingredient",
    "MealEvent",
    "MealState",
    "Nutrition",
    "PortionSize",
    "VisionResult",
    "MealRecognitionRecord",
    # engagement / clinical card
    "EngagementMetrics",
    "ClinicalCardRecord",
    # emotion
    "EmotionLabel",
    "EmotionConfidenceBand",
    "EmotionEvidence",
    "EmotionInferenceResult",
    "EmotionRuntimeHealth",
    # inference
    "InferenceModality",
    "ProviderMetadata",
    "InferenceRequest",
    "InferenceResponse",
    "InferenceHealth",
    # role / profile tools
    "CaregiverToolState",
    "ClinicalSummaryToolState",
    "SelfToolState",
    "AgentRoleToolContract",
    "RoleToolContract",
    # social
    "BlockScore",
    "CommunityChallenge",
    # lazy domain.meals re-exports
    "CanonicalFoodAdvice",
    "CanonicalFoodAlternative",
    "CanonicalFoodRecord",
    "MealNutritionProfile",
    "MealPerception",
    "MealPortionEstimate",
    "NormalizedMealItem",
    "EnrichedMealEvent",
    "PortionReference",
    "RawFoodSourceRecord",
]
