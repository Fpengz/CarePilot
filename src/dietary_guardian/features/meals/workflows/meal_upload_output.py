from __future__ import annotations

from pydantic import BaseModel

from dietary_guardian.core.contracts.agent_envelopes import AgentOutputEnvelope
from dietary_guardian.features.meals.domain.models import (
    NutritionRiskProfile,
    RawObservationBundle,
    ValidatedMealEvent,
)
from dietary_guardian.platform.observability.workflows.domain.models import WorkflowExecutionResult


class MealUploadOutput(BaseModel):
    raw_observation: RawObservationBundle
    validated_event: ValidatedMealEvent
    nutrition_profile: NutritionRiskProfile
    output_envelope: AgentOutputEnvelope
    workflow: WorkflowExecutionResult

