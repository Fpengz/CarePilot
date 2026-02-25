from fastapi.testclient import TestClient

from apps.api.dietary_api.main import create_app


def test_health_endpoints() -> None:
    client = TestClient(create_app())

    live = client.get("/api/v1/health/live")
    ready = client.get("/api/v1/health/ready")
    config = client.get("/api/v1/health/config")

    assert live.status_code == 200
    assert ready.status_code == 200
    assert config.status_code == 200
    assert "llm_provider" in config.json()

