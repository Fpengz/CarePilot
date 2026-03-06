from pydantic import BaseModel, Field

from dietary_guardian.models.workflow import WorkflowName


class AgentContract(BaseModel):
    agent_id: str
    capabilities: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    output_contract: str


class WorkflowRuntimeStep(BaseModel):
    step_id: str
    agent_id: str
    capability: str
    tool_names: list[str] = Field(default_factory=list)


class WorkflowRuntimeContract(BaseModel):
    workflow_name: WorkflowName
    steps: list[WorkflowRuntimeStep] = Field(default_factory=list)
