from fastapi.testclient import TestClient

from apps.api.dietary_api.main import create_app


def _login(client: TestClient, email: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_tool_policy_crud_and_shadow_evaluation_for_admin() -> None:
    client = TestClient(create_app())
    _login(client, "admin@example.com", "admin-pass")

    create_response = client.post(
        "/api/v1/workflows/tool-policies",
        json={
            "role": "admin",
            "agent_id": "notification_agent",
            "tool_name": "trigger_alert",
            "effect": "deny",
            "conditions": {"environment": "dev"},
            "priority": 100,
            "enabled": True,
        },
    )
    assert create_response.status_code == 200
    policy = create_response.json()["policy"]
    assert policy["effect"] == "deny"
    assert policy["enabled"] is True

    list_response = client.get("/api/v1/workflows/tool-policies")
    assert list_response.status_code == 200
    policies = list_response.json()["items"]
    assert any(item["id"] == policy["id"] for item in policies)

    eval_response = client.get(
        "/api/v1/workflows/tool-policies/evaluation",
        params={
            "role": "admin",
            "agent_id": "notification_agent",
            "tool_name": "trigger_alert",
            "environment": "dev",
        },
    )
    assert eval_response.status_code == 200
    body = eval_response.json()
    assert body["policy_mode"] == "shadow"
    assert body["code_decision"] == "allow"
    assert body["db_decision"] == "deny"
    assert body["effective_decision"] == "allow"

    patch_response = client.patch(
        f"/api/v1/workflows/tool-policies/{policy['id']}",
        json={"enabled": False},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["policy"]["enabled"] is False


def test_tool_policy_endpoints_forbidden_for_member() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    assert client.get("/api/v1/workflows/tool-policies").status_code == 403
    assert (
        client.post(
            "/api/v1/workflows/tool-policies",
            json={
                "role": "member",
                "agent_id": "notification_agent",
                "tool_name": "trigger_alert",
                "effect": "deny",
            },
        ).status_code
        == 403
    )


def test_runtime_contract_snapshot_endpoints_for_admin() -> None:
    client = TestClient(create_app())
    _login(client, "admin@example.com", "admin-pass")

    list_response = client.get("/api/v1/workflows/runtime-contract/snapshots")
    assert list_response.status_code == 200
    first = list_response.json()["items"]
    assert first

    create_response = client.post("/api/v1/workflows/runtime-contract/snapshots")
    assert create_response.status_code == 200
    created = create_response.json()["snapshot"]
    assert created["source"] == "manual_api"
    assert created["version"] >= 1

    compare_response = client.get(
        "/api/v1/workflows/runtime-contract/snapshots/compare",
        params={"base_version": created["version"], "target_version": created["version"]},
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()
    assert compare["changed"] is False
    assert compare["base_version"] == created["version"]
    assert compare["target_version"] == created["version"]


def test_runtime_contract_snapshot_endpoints_forbidden_for_member() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    assert client.get("/api/v1/workflows/runtime-contract/snapshots").status_code == 403
    assert client.post("/api/v1/workflows/runtime-contract/snapshots").status_code == 403
