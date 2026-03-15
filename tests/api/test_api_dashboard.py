"""Tests for the dashboard analytics API."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, date, datetime, time, timedelta

import pytest
from apps.api.carepilot_api.main import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient

from care_pilot.config.app import get_settings
from care_pilot.features.companion.core.health.models import (
    BiomarkerReading,
    HealthProfileRecord,
    MedicationAdherenceEvent,
)
from care_pilot.features.meals.domain.models import (
    NutritionRiskProfile,
    ValidatedMealEvent,
)
from care_pilot.features.reminders.domain.models import ReminderEvent


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_dashboard_env(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
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
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200


def _dt(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour=hour, tzinfo=UTC))


def _seed_dashboard_state(client: TestClient) -> None:
    app = client.app
    assert isinstance(app, FastAPI)
    stores = app.state.ctx.stores

    stores.profiles.save_health_profile(
        HealthProfileRecord(
            user_id="user_001",
            locale="en-SG",
            daily_protein_target_g=80,
            daily_fiber_target_g=30,
            daily_sugar_limit_g=28,
            target_calories_per_day=1900,
            nutrition_goals=["lower_sugar", "heart_health"],
        )
    )

    base_day = date(2026, 3, 14)
    for offset in range(0, 42):
        current_day = base_day - timedelta(days=offset)
        breakfast_at = _dt(current_day, 8)
        dinner_at = _dt(current_day, 19)

        breakfast_event = ValidatedMealEvent(
            event_id=f"meal-breakfast-{offset}",
            user_id="user_001",
            captured_at=breakfast_at,
            meal_name="Breakfast bowl",
        )
        dinner_event = ValidatedMealEvent(
            event_id=f"meal-dinner-{offset}",
            user_id="user_001",
            captured_at=dinner_at,
            meal_name="Dinner plate",
        )
        stores.meals.save_validated_meal_event(breakfast_event)
        stores.meals.save_validated_meal_event(dinner_event)

        stores.meals.save_nutrition_risk_profile(
            NutritionRiskProfile(
                profile_id=f"risk-breakfast-{offset}",
                event_id=breakfast_event.event_id,
                user_id="user_001",
                captured_at=breakfast_at,
                calories=420 + offset,
                carbs_g=42 + (offset % 5),
                protein_g=26,
                fat_g=14,
                fiber_g=8,
                sugar_g=11,
                sodium_mg=380,
                risk_tags=["balanced"] if offset % 3 else ["high_hba1c"],
            )
        )
        stores.meals.save_nutrition_risk_profile(
            NutritionRiskProfile(
                profile_id=f"risk-dinner-{offset}",
                event_id=dinner_event.event_id,
                user_id="user_001",
                captured_at=dinner_at,
                calories=790 + (offset * 2),
                carbs_g=74,
                protein_g=34,
                fat_g=25,
                fiber_g=6,
                sugar_g=16,
                sodium_mg=720,
                risk_tags=["high_ldl"] if offset % 4 == 0 else [],
            )
        )

        status = "taken" if offset % 5 else "missed"
        stores.medications.save_medication_adherence_event(
            MedicationAdherenceEvent(
                id=f"adherence-{offset}",
                user_id="user_001",
                regimen_id="regimen-1",
                status=status,
                scheduled_at=_dt(current_day, 9),
                taken_at=_dt(current_day, 9) if status == "taken" else None,
                source="manual",
            )
        )

        reminder_status = "missed" if offset == 0 else "sent"
        stores.reminders.save_reminder_event(
            ReminderEvent(
                id=f"reminder-{offset}",
                user_id="user_001",
                title="Evening medication",
                medication_name="Metformin",
                scheduled_at=_dt(current_day, 21),
                dosage_text="500mg",
                status=reminder_status,
                sent_at=_dt(current_day, 21),
            )
        )

    stores.biomarkers.save_biomarker_readings(
        "user_001",
        [
            BiomarkerReading(
                name="hba1c",
                value=7.5,
                measured_at=datetime(2026, 1, 20, tzinfo=UTC),
            ),
            BiomarkerReading(
                name="hba1c",
                value=7.1,
                measured_at=datetime(2026, 2, 20, tzinfo=UTC),
            ),
            BiomarkerReading(
                name="hba1c",
                value=6.8,
                measured_at=datetime(2026, 3, 12, tzinfo=UTC),
            ),
            BiomarkerReading(
                name="ldl",
                value=4.2,
                measured_at=datetime(2026, 1, 20, tzinfo=UTC),
            ),
            BiomarkerReading(
                name="ldl",
                value=3.9,
                measured_at=datetime(2026, 3, 12, tzinfo=UTC),
            ),
        ],
    )


def test_dashboard_overview_requires_authentication(
    sqlite_dashboard_env: None,
) -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/dashboard?range=30d")

    assert response.status_code == 401


def test_dashboard_overview_returns_daily_analytics_for_last_30_days(
    sqlite_dashboard_env: None,
) -> None:
    client = TestClient(create_app())
    _login(client)
    _seed_dashboard_state(client)

    response = client.get("/api/v1/dashboard?range=30d")

    assert response.status_code == 200
    body = response.json()
    assert body["range"]["key"] == "30d"
    assert body["range"]["bucket"] == "day"
    assert body["summary"]["nutrition_goal_score"]["value"] >= 0
    assert body["summary"]["adherence_score"]["value"] >= 0
    assert body["summary"]["glycemic_risk"]["status"] in {
        "stable",
        "watch",
        "elevated",
    }
    assert body["alerts"]
    assert body["charts"]["calories"]["bucket"] == "day"
    assert body["charts"]["macros"]["bucket"] == "day"
    assert body["charts"]["glycemic_risk"]["bucket"] == "day"
    assert body["charts"]["adherence"]["bucket"] == "day"
    assert len(body["charts"]["meal_timing"]["bins"]) == 24
    assert body["insights"]["recommendations"]
    assert body["links"]["meals"] == "/meals"


def test_dashboard_overview_uses_hourly_buckets_for_today(
    sqlite_dashboard_env: None,
) -> None:
    client = TestClient(create_app())
    _login(client)
    _seed_dashboard_state(client)

    response = client.get("/api/v1/dashboard?range=today")

    assert response.status_code == 200
    body = response.json()
    assert body["range"]["key"] == "today"
    assert body["range"]["bucket"] == "hour"
    assert body["charts"]["calories"]["bucket"] == "hour"
    assert any(
        point["value"] > 0 for point in body["charts"]["calories"]["points"]
    )
    assert any(
        bin_item["count"] > 0
        for bin_item in body["charts"]["meal_timing"]["bins"]
    )


def test_dashboard_overview_supports_custom_ranges_and_weekly_rollups(
    sqlite_dashboard_env: None,
) -> None:
    client = TestClient(create_app())
    _login(client)
    _seed_dashboard_state(client)

    response = client.get(
        "/api/v1/dashboard?range=custom&from=2026-01-01&to=2026-03-14"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["range"]["key"] == "custom"
    assert body["range"]["from"] == "2026-01-01"
    assert body["range"]["to"] == "2026-03-14"
    assert body["range"]["bucket"] == "week"
    assert body["charts"]["calories"]["bucket"] == "week"
    assert len(body["charts"]["calories"]["points"]) >= 6
