from __future__ import annotations

from pydantic import BaseModel

from dietary_guardian.platform.observability.workflows.domain.models import WorkflowExecutionResult


class PrescriptionIngestOutput(BaseModel):
    status: str
    workflow: WorkflowExecutionResult

