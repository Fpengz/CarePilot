from __future__ import annotations

from pydantic import BaseModel

from care_pilot.core.contracts.agent_envelopes import AgentOutputEnvelope
from care_pilot.features.meals.domain.models import (
    MealCandidateRecord,
    NutritionRiskProfile,
    RawObservationBundle,
    ValidatedMealEvent,
)
from care_pilot.platform.observability.workflows.domain.models import (
    WorkflowExecutionResult,
)


class MealUploadOutput(BaseModel):
    raw_observation: RawObservationBundle
    candidate_record: MealCandidateRecord
    confirmation_required: bool = False
    validated_event: ValidatedMealEvent | None = None
    nutrition_profile: NutritionRiskProfile | None = None
    output_envelope: AgentOutputEnvelope
    workflow: WorkflowExecutionResult
