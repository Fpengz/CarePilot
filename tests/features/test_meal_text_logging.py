"""Ensure manual meal logging from text creates persisted nutrition profiles."""

from __future__ import annotations

from pathlib import Path

from dietary_guardian.platform.persistence.domain_stores import build_app_stores
from dietary_guardian.platform.persistence.sqlite_repository import SQLiteRepository

from dietary_guardian.features.meals.use_cases import log_meal_from_text


def test_log_meal_from_text_persists_event_and_profile(tmp_path: Path) -> None:
    db_path = tmp_path / "meals.db"
    app_store = SQLiteRepository(str(db_path))
    stores = build_app_stores(app_store)

    result = log_meal_from_text(
        user_id="user-1",
        meal_text="Chicken rice",
        food_store=stores.foods,
        meals_store=stores.meals,
    )

    assert "chicken" in result.validated_event.meal_name.lower()
    assert result.nutrition_profile.calories >= 0

    events = stores.meals.list_validated_meal_events("user-1")
    profiles = stores.meals.list_nutrition_risk_profiles("user-1")
    assert len(events) == 1
    assert len(profiles) == 1
