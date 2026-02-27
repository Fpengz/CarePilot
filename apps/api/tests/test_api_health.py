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


def test_request_context_headers_are_emitted_and_passthrough() -> None:
    client = TestClient(create_app())

    generated = client.get("/api/v1/health/live")
    assert generated.status_code == 200
    assert generated.headers.get("x-request-id")
    assert generated.headers.get("x-correlation-id")

    custom = client.get(
        "/api/v1/health/live",
        headers={
            "X-Request-ID": "req-custom-123",
            "X-Correlation-ID": "corr-custom-456",
        },
    )
    assert custom.status_code == 200
    assert custom.headers.get("x-request-id") == "req-custom-123"
    assert custom.headers.get("x-correlation-id") == "corr-custom-456"
