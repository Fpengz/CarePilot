"""Static agent and workflow contract registry for the runtime layer."""

from dietary_guardian.domain.workflows.models import (
    AgentContract,
    WorkflowName,
    WorkflowRuntimeContract,
    WorkflowRuntimeStep,
)


class AgentRegistry:
    def __init__(self, *, agents: list[AgentContract], workflow_contracts: list[WorkflowRuntimeContract]) -> None:
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
        AgentContract(agent_id="meal_analysis_agent", capabilities=["meal_perception", "meal_normalization"], allowed_tools=[], output_contract="vision_result_with_enriched_event"),
        AgentContract(agent_id="dietary_agent", capabilities=["nutrition_risk_assessment", "dietary_reasoning"], allowed_tools=[], output_contract="dietary_reasoning_response"),
        AgentContract(agent_id="recommendation_agent", capabilities=["daily_recommendation", "substitution_ranking"], allowed_tools=[], output_contract="daily_recommendation_bundle"),
        AgentContract(agent_id="emotion_agent", capabilities=["emotion_inference"], allowed_tools=[], output_contract="emotion_inference_result"),
        AgentContract(agent_id="notification_agent", capabilities=["alert_emit", "timeline_emit"], allowed_tools=["trigger_alert"], output_contract="alert_or_timeline_event"),
    ]
    contracts = [
        WorkflowRuntimeContract(
            workflow_name=WorkflowName.MEAL_ANALYSIS,
            steps=[
                WorkflowRuntimeStep(step_id="meal_analysis", agent_id="meal_analysis_agent", capability="meal_perception", tool_names=[]),
                WorkflowRuntimeStep(step_id="dietary_reasoning", agent_id="dietary_agent", capability="nutrition_risk_assessment", tool_names=[]),
                WorkflowRuntimeStep(step_id="emit_timeline", agent_id="notification_agent", capability="timeline_emit", tool_names=[]),
            ],
        ),
        WorkflowRuntimeContract(
            workflow_name=WorkflowName.ALERT_ONLY,
            steps=[WorkflowRuntimeStep(step_id="emit_alert", agent_id="notification_agent", capability="alert_emit", tool_names=["trigger_alert"])],
        ),
        WorkflowRuntimeContract(
            workflow_name=WorkflowName.REPORT_PARSE,
            steps=[
                WorkflowRuntimeStep(step_id="parse_report", agent_id="meal_analysis_agent", capability="meal_normalization", tool_names=[]),
                WorkflowRuntimeStep(step_id="summarize", agent_id="dietary_agent", capability="dietary_reasoning", tool_names=[]),
            ],
        ),
    ]
    return AgentRegistry(agents=agents, workflow_contracts=contracts)
