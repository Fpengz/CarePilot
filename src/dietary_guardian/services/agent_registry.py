from dietary_guardian.models.agent_runtime import AgentContract, WorkflowRuntimeContract, WorkflowRuntimeStep
from dietary_guardian.models.workflow import WorkflowName


class AgentRegistry:
    def __init__(
        self,
        *,
        agents: list[AgentContract],
        workflow_contracts: list[WorkflowRuntimeContract],
    ) -> None:
        self._agents = {agent.agent_id: agent for agent in agents}
        self._workflow_contracts = {contract.workflow_name: contract for contract in workflow_contracts}

    def list_agents(self) -> list[AgentContract]:
        return list(self._agents.values())

    def list_workflow_contracts(self) -> list[WorkflowRuntimeContract]:
        return list(self._workflow_contracts.values())

    def get_workflow_contract(self, workflow_name: WorkflowName) -> WorkflowRuntimeContract | None:
        return self._workflow_contracts.get(workflow_name)


def build_default_agent_registry() -> AgentRegistry:
    agents = [
        AgentContract(
            agent_id="perception_agent",
            capabilities=["meal_perception", "report_parse"],
            allowed_tools=[],
            output_contract="meal_state_or_parsed_readings",
        ),
        AgentContract(
            agent_id="clinical_reasoning_agent",
            capabilities=["nutrition_risk_assessment", "clinical_summary"],
            allowed_tools=[],
            output_contract="clinical_interpretation",
        ),
        AgentContract(
            agent_id="notification_agent",
            capabilities=["alert_emit", "timeline_emit"],
            allowed_tools=["trigger_alert"],
            output_contract="alert_or_timeline_event",
        ),
    ]
    contracts = [
        WorkflowRuntimeContract(
            workflow_name=WorkflowName.MEAL_ANALYSIS,
            steps=[
                WorkflowRuntimeStep(
                    step_id="perception",
                    agent_id="perception_agent",
                    capability="meal_perception",
                    tool_names=[],
                ),
                WorkflowRuntimeStep(
                    step_id="handoff_clinical",
                    agent_id="clinical_reasoning_agent",
                    capability="nutrition_risk_assessment",
                    tool_names=[],
                ),
                WorkflowRuntimeStep(
                    step_id="emit_timeline",
                    agent_id="notification_agent",
                    capability="timeline_emit",
                    tool_names=[],
                ),
            ],
        ),
        WorkflowRuntimeContract(
            workflow_name=WorkflowName.ALERT_ONLY,
            steps=[
                WorkflowRuntimeStep(
                    step_id="emit_alert",
                    agent_id="notification_agent",
                    capability="alert_emit",
                    tool_names=["trigger_alert"],
                ),
            ],
        ),
        WorkflowRuntimeContract(
            workflow_name=WorkflowName.REPORT_PARSE,
            steps=[
                WorkflowRuntimeStep(
                    step_id="parse_report",
                    agent_id="perception_agent",
                    capability="report_parse",
                    tool_names=[],
                ),
                WorkflowRuntimeStep(
                    step_id="summarize",
                    agent_id="clinical_reasoning_agent",
                    capability="clinical_summary",
                    tool_names=[],
                ),
            ],
        ),
    ]
    return AgentRegistry(agents=agents, workflow_contracts=contracts)
