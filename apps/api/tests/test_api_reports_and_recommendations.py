"""Module for test api reports and recommendations."""

from collections.abc import Generator
from io import BytesIO

import pytest
from apps.api.dietary_api.main import create_app
from fastapi.testclient import TestClient
from PIL import Image

from dietary_guardian.config.app import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_reports_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient, email: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def _meal_upload(client: TestClient) -> None:
    img = Image.new("RGB", (64, 64), color=(0, 255, 0))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", buf.getvalue(), "image/jpeg")},
        data={"runtime_mode": "local", "provider": "test"},
    )
    assert response.status_code == 200


def test_reports_parse_text_returns_readings_and_snapshot(sqlite_reports_env: None) -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    response = client.post(
        "/api/v1/reports/parse",
        json={"source": "pasted_text", "text": "HbA1c 7.1 LDL 4.2 systolic bp 150 diastolic bp 95"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["readings"]
    assert "hba1c" in body["snapshot"]["biomarkers"]
    assert "high_ldl" in body["snapshot"]["risk_flags"]


def test_recommendations_generate_uses_latest_meal_and_snapshot(sqlite_reports_env: None) -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")
    _meal_upload(client)
    parse_resp = client.post(
        "/api/v1/reports/parse",
        json={"source": "pasted_text", "text": "HbA1c 7.1 LDL 4.2"},
    )
    assert parse_resp.status_code == 200

    response = client.post("/api/v1/recommendations/generate")

    assert response.status_code == 200
    body = response.json()
    assert "recommendation" in body
    assert "workflow" in body
    assert body["recommendation"]["safe"] in {True, False}


def test_recommendations_generate_requires_meal_records(sqlite_reports_env: None) -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    response = client.post("/api/v1/recommendations/generate")

    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == "no meal records available"
    assert body["error"]["code"] == "recommendations.no_meal_records"


def test_recommendations_generate_requires_clinical_snapshot(sqlite_reports_env: None) -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")
    _meal_upload(client)

    response = client.post("/api/v1/recommendations/generate")

    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == "no clinical snapshot available"
    assert body["error"]["code"] == "recommendations.no_clinical_snapshot"


def test_recommendations_generate_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_RATE_LIMIT_RECOMMENDATIONS_GENERATE_MAX_REQUESTS", "1")
    _reset_settings_cache()
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")
    _meal_upload(client)
    parsed = client.post(
        "/api/v1/reports/parse",
        json={"source": "pasted_text", "text": "HbA1c 7.1 LDL 4.2"},
    )
    assert parsed.status_code == 200

    first = client.post("/api/v1/recommendations/generate")
    second = client.post("/api/v1/recommendations/generate")
    _reset_settings_cache()

    assert first.status_code == 200
    assert second.status_code == 429
    body = second.json()
    assert body["detail"] == "rate limit exceeded"
    assert body["error"]["code"] == "recommendations.generate.rate_limited"


def test_reports_parse_includes_symptom_summary_and_workflow_trace(sqlite_reports_env: None) -> None:
    app = create_app()
    member_client = TestClient(app)
    admin_client = TestClient(app)
    _login(member_client, "member@example.com", "member-pass")
    _login(admin_client, "admin@example.com", "admin-pass")

    first_checkin = member_client.post(
        "/api/v1/symptoms/check-ins",
        json={
            "severity": 2,
            "symptom_codes": ["fatigue"],
            "free_text": "Mild fatigue",
        },
    )
    assert first_checkin.status_code == 200
    second_checkin = member_client.post(
        "/api/v1/symptoms/check-ins",
        json={
            "severity": 5,
            "symptom_codes": ["chest_pain"],
            "free_text": "Chest pain and trouble breathing",
        },
    )
    assert second_checkin.status_code == 200

    response = member_client.post(
        "/api/v1/reports/parse",
        json={"source": "pasted_text", "text": "HbA1c 7.1 LDL 4.2 systolic bp 150 diastolic bp 95"},
        headers={"X-Request-ID": "req-report-parse-1", "X-Correlation-ID": "corr-report-parse-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symptom_summary"]["total_count"] == 2
    assert body["symptom_summary"]["red_flag_count"] == 1
    assert body["symptom_summary"]["average_severity"] == 3.5
    assert body["symptom_window"]["from"] is not None
    assert body["symptom_window"]["to"] is not None
    assert body["symptom_window"]["limit"] == 1000

    replay = admin_client.get("/api/v1/workflows/corr-report-parse-1")
    assert replay.status_code == 200
    workflow_body = replay.json()
    assert workflow_body["workflow_name"] == "replay"
    event_types = [event["event_type"] for event in workflow_body["timeline_events"]]
    event_workflows = [event.get("workflow_name") for event in workflow_body["timeline_events"]]
    assert "workflow_started" in event_types
    assert "workflow_completed" in event_types
    assert "report_parse" in event_workflows
