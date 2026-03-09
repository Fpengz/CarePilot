from dietary_guardian.models.tooling import ToolPolicyContext
from dietary_guardian.services.platform_tools import build_platform_tool_registry
from dietary_guardian.infrastructure.persistence import SQLiteRepository


def test_trigger_alert_tool_allows_admin_scope(tmp_path) -> None:
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
        context=ToolPolicyContext(account_role="admin", scopes=["alert:trigger"], environment="dev", user_id="u1"),
    )

    assert result.success is True
    assert result.error is None


def test_trigger_alert_tool_blocks_member_without_scope(tmp_path) -> None:
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
        context=ToolPolicyContext(account_role="member", scopes=[], environment="dev", user_id="u1"),
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.classification == "policy_blocked"
