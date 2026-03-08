from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from apps.api.dietary_api.main import create_app
from dietary_guardian.config.settings import get_settings
from dietary_guardian.models.meal import MealState, Nutrition
from dietary_guardian.models.meal_record import MealRecognitionRecord


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_meal_weekly_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient, email: str = "member@example.com", password: str = "member-pass") -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def _seed_meal(app, *, meal_id: str, captured_at: datetime, calories: float, sugar_g: float, sodium_mg: float) -> None:
    app.state.ctx.app_store.save_meal_record(
        MealRecognitionRecord(
            id=meal_id,
            user_id="user_001",
            captured_at=captured_at,
            source="upload",
            meal_state=MealState(
                dish_name=f"Meal {meal_id}",
                confidence_score=0.9,
                identification_method="AI_Flash",
                ingredients=[],
                nutrition=Nutrition(
                    calories=calories,
                    carbs_g=50,
                    sugar_g=sugar_g,
                    protein_g=20,
                    fat_g=10,
                    sodium_mg=sodium_mg,
                    fiber_g=4,
                ),
            ),
            analysis_version="test",
            multi_item_count=1,
        )
    )


def test_meal_weekly_summary_returns_rollup(sqlite_meal_weekly_env: None) -> None:
    app = create_app()
    client = TestClient(app)
    _login(client)

    _seed_meal(
        app,
        meal_id="meal_w_1",
        captured_at=datetime(2026, 3, 2, 8, tzinfo=timezone.utc),
        calories=600,
        sugar_g=9,
        sodium_mg=900,
    )
    _seed_meal(
        app,
        meal_id="meal_w_2",
        captured_at=datetime(2026, 3, 4, 12, tzinfo=timezone.utc),
        calories=700,
        sugar_g=11,
        sodium_mg=1100,
    )

    response = client.get("/api/v1/meal/weekly-summary?week_start=2026-03-02")

    assert response.status_code == 200
    body = response.json()
    assert body["week_start"] == "2026-03-02"
    assert body["week_end"] == "2026-03-08"
    assert body["meal_count"] == 2
    assert body["totals"]["calories"] == pytest.approx(1300.0)
    assert body["daily_breakdown"]["2026-03-02"]["meal_count"] == 1
