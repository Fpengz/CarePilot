from dietary_guardian.agents.registry import build_default_agent_registry
from dietary_guardian.domain.workflows.models import WorkflowName


def test_default_agent_registry_exposes_core_workflow_contracts() -> None:
    registry = build_default_agent_registry()
    workflow_names = {contract.workflow_name for contract in registry.list_workflow_contracts()}

    assert WorkflowName.MEAL_ANALYSIS in workflow_names
    assert WorkflowName.ALERT_ONLY in workflow_names
    assert WorkflowName.REPORT_PARSE in workflow_names

    meal_contract = registry.get_workflow_contract(WorkflowName.MEAL_ANALYSIS)
    assert meal_contract is not None
    assert [step.step_id for step in meal_contract.steps] == [
        "meal_analysis",
        "dietary_reasoning",
        "emit_timeline",
    ]

    agent_ids = {agent.agent_id for agent in registry.list_agents()}
    assert "meal_analysis_agent" in agent_ids
    assert "dietary_agent" in agent_ids
    assert "recommendation_agent" in agent_ids
    assert "emotion_agent" in agent_ids
    assert "notification_agent" in agent_ids
