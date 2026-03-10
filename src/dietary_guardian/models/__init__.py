"""Local model definitions that have not yet migrated to domain subpackages.

Domain types (alerts, health, identity, notifications, recommendations, workflows)
now live in their respective ``dietary_guardian.domain.*`` modules. Import from
those directly; this package only exposes types that are still canonical here.
"""

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
]
