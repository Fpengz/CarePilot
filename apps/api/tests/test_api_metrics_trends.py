"""Module for test api metrics trends."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from apps.api.dietary_api.main import create_app
from fastapi.testclient import TestClient

from dietary_guardian.config.app import get_settings
from dietary_guardian.domain.health.models import BiomarkerReading


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_metrics_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient, email: str = "member@example.com", password: str = "member-pass") -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_metrics_trends_for_biomarkers(sqlite_metrics_env: None) -> None:
    app = create_app()
    client = TestClient(app)
    _login(client)

    app.state.ctx.app_store.save_biomarker_readings(
        "user_001",
        [
            BiomarkerReading(name="ldl", value=4.5, measured_at=datetime(2026, 3, 1, tzinfo=timezone.utc)),
            BiomarkerReading(name="ldl", value=3.8, measured_at=datetime(2026, 3, 5, tzinfo=timezone.utc)),
        ],
    )

    response = client.get("/api/v1/metrics/trends?metric=biomarker:ldl")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["metric"] == "biomarker:ldl"
    assert len(item["points"]) == 2
    assert item["delta"] == pytest.approx(-0.7)
    assert item["direction"] == "decrease"
