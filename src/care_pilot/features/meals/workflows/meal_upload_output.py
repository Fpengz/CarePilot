from __future__ import annotations

from pydantic import BaseModel

from care_pilot.core.contracts.agent_envelopes import AgentOutputEnvelope
from care_pilot.features.meals.domain.models import (
    NutritionRiskProfile,
    RawObservationBundle,
    ValidatedMealEvent,
)
from care_pilot.platform.observability.workflows.domain.models import (
    WorkflowExecutionResult,
)


class MealUploadOutput(BaseModel):
    raw_observation: RawObservationBundle
    validated_event: ValidatedMealEvent
    nutrition_profile: NutritionRiskProfile
    output_envelope: AgentOutputEnvelope
    workflow: WorkflowExecutionResult
