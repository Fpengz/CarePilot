"""Tests for the synthetic data developer CLI."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from apps.api.carepilot_api.main import create_app
from fastapi.testclient import TestClient
from scripts.cli import app
from typer.testing import CliRunner

from care_pilot.config.app import get_settings
from care_pilot.platform.persistence.sqlite_repository import SQLiteRepository

runner = CliRunner()


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_seed_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(
    client: TestClient,
    email: str = "member@example.com",
    password: str = "member-pass",
) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_seed_synthetic_requires_explicit_reset_or_append(
    sqlite_seed_env: None,
) -> None:
    result = runner.invoke(app, ["seed", "synthetic", "--days", "14"])

    assert result.exit_code == 2
    assert "choose exactly one of --reset or --append" in result.output


def test_seed_synthetic_populates_dashboard_ready_data(
    sqlite_seed_env: None,
) -> None:
    result = runner.invoke(
        app,
        [
            "seed",
            "synthetic",
            "--reset",
            "--days",
            "45",
            "--seed",
            "17",
            "--profile",
            "improving",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "seed.synthetic.complete" in result.stdout

    repo = SQLiteRepository(get_settings().storage.api_sqlite_db_path)
    profiles = repo.list_nutrition_risk_profiles("user_001")
    meals = repo.list_validated_meal_events("user_001")
    readings = repo.list_biomarker_readings("user_001")
    adherence = repo.list_medication_adherence_events(user_id="user_001")
    reminders = repo.list_reminder_events("user_001")

    assert len(profiles) > 30
    assert len(meals) == len(profiles)
    assert any(reading.name == "weight_kg" for reading in readings)
    assert any(reading.name == "hba1c" for reading in readings)
    assert len(adherence) >= 30
    assert len(reminders) >= 30

    client = TestClient(create_app())
    _login(client)
    dashboard = client.get("/api/v1/dashboard?range=30d")
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["alerts"]
    assert any(point["value"] > 0 for point in body["charts"]["calories"]["points"])


def test_seed_synthetic_append_adds_newer_records(
    sqlite_seed_env: None,
) -> None:
    first = runner.invoke(
        app,
        [
            "seed",
            "synthetic",
            "--reset",
            "--days",
            "14",
            "--seed",
            "7",
            "--profile",
            "stable",
        ],
    )
    assert first.exit_code == 0, first.stdout

    repo = SQLiteRepository(get_settings().storage.api_sqlite_db_path)
    before = repo.list_nutrition_risk_profiles("user_001")
    before_latest = max(item.captured_at for item in before)

    second = runner.invoke(
        app,
        [
            "seed",
            "synthetic",
            "--append",
            "--days",
            "7",
            "--seed",
            "7",
            "--profile",
            "stable",
        ],
    )
    assert second.exit_code == 0, second.stdout

    after = repo.list_nutrition_risk_profiles("user_001")
    after_latest = max(item.captured_at for item in after)

    assert len(after) > len(before)
    assert after_latest > before_latest
