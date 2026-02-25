import pytest

from dietary_guardian.models.tooling import ToolPolicyContext
from dietary_guardian.services.platform_tools import build_platform_tool_registry
from dietary_guardian.services.repository import SQLiteRepository


@pytest.mark.parametrize("role", ["patient", "caregiver", "clinician"])
def test_trigger_alert_tool_allows_roles_exposed_in_streamlit_ui(tmp_path, role: str) -> None:
    repo = SQLiteRepository(str(tmp_path / "alerts.db"))
    registry = build_platform_tool_registry(repo)

    result = registry.execute(
        "trigger_alert",
        {
            "alert_type": "manual_test_alert",
            "severity": "warning",
            "message": "Manual end-to-end alert verification",
            "destinations": ["in_app"],
        },
        context=ToolPolicyContext(role=role, environment="dev", user_id="u1"),
    )

    assert result.success is True
    assert result.error is None
