from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from dietary_guardian.models.agent_runtime import AgentContract, WorkflowRuntimeContract

WorkflowContractSnapshotSource = Literal["startup_bootstrap", "manual_api"]


class WorkflowContractSnapshotRecord(BaseModel):
    id: str
    version: int
    contract_hash: str
    source: WorkflowContractSnapshotSource
    workflows: list[WorkflowRuntimeContract] = Field(default_factory=list)
    agents: list[AgentContract] = Field(default_factory=list)
    created_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
