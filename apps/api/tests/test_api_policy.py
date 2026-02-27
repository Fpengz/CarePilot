from typing import Any

import pytest
from fastapi import HTTPException

from apps.api.dietary_api.policy import POLICY_RULES, authorize_action, authorize_resource_action


def _session(scopes: list[str], *, account_role: str = "member") -> dict[str, Any]:
    return {
        "session_id": "s1",
        "user_id": "user_001",
        "email": "member@example.com",
        "account_role": account_role,
        "profile_mode": "self",
        "display_name": "Alex",
        "scopes": scopes,
    }


def test_policy_table_contains_core_actions() -> None:
    for action in (
        "meal.analyze",
        "meal.records.read",
        "suggestions.generate",
        "suggestions.read",
        "alerts.trigger",
        "alerts.timeline.read",
        "workflows.read",
        "workflows.replay",
        "auth.audit.read",
        "auth.sessions.revoke",
    ):
        assert action in POLICY_RULES


def test_authorize_action_rejects_missing_scope() -> None:
    with pytest.raises(HTTPException) as exc_info:
        authorize_action(_session(scopes=[]), action="suggestions.read")
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


def test_authorize_action_allows_required_scope() -> None:
    authorize_action(_session(scopes=["report:read"]), action="suggestions.read")


def test_authorize_resource_action_rejects_non_owner() -> None:
    with pytest.raises(HTTPException) as exc_info:
        authorize_resource_action(
            _session(scopes=[]),
            action="auth.sessions.revoke",
            resource={"owner_user_id": "user_999"},
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "session not found"


def test_authorize_resource_action_allows_owner() -> None:
    authorize_resource_action(
        _session(scopes=[]),
        action="auth.sessions.revoke",
        resource={"owner_user_id": "user_001"},
    )
