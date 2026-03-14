from __future__ import annotations

from pydantic import BaseModel, Field

from dietary_guardian.core.contracts.agent_envelopes import CaptureEnvelope
from dietary_guardian.features.meals.domain.models import (
    ContextSnapshot,
    DietaryClaims,
    ImageInput,
    NutritionRiskProfile,
    RawObservationBundle,
    ValidatedMealEvent,
    VisionResult,
)


class MealUploadState(BaseModel):
    request_id: str
    correlation_id: str
    user_id: str
    profile_mode: str | None = None

    capture: CaptureEnvelope
    image_input: ImageInput
    provider: str | None = None
    meal_text: str | None = None
    context: ContextSnapshot

    # Intermediate results
    claims: DietaryClaims | None = None
    unresolved_conflicts: list[str] = Field(default_factory=list)
    vision_result: VisionResult | None = None
    raw_observation: RawObservationBundle | None = None
    validated_event: ValidatedMealEvent | None = None
    nutrition_profile: NutritionRiskProfile | None = None

