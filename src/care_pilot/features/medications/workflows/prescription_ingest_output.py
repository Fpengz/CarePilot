from __future__ import annotations

from pydantic import BaseModel

from care_pilot.platform.observability.workflows.domain.models import (
    WorkflowExecutionResult,
)


class PrescriptionIngestOutput(BaseModel):
    status: str
    workflow: WorkflowExecutionResult
