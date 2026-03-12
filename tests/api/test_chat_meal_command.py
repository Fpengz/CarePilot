"""Tests for chat meal command parsing and logging."""

from pathlib import Path

from apps.api.dietary_api.routers.chat import _parse_meal_command, _log_meal_command
from dietary_guardian.platform.persistence.domain_stores import build_app_stores
from dietary_guardian.platform.persistence.sqlite_repository import SQLiteRepository


def test_parse_meal_command_accepts_bracket_prefix() -> None:
    assert _parse_meal_command("[MEAL] chicken rice") == "chicken rice"


def test_parse_meal_command_accepts_colon_prefix() -> None:
    assert _parse_meal_command("meal: soft-boiled eggs with toast") == "soft-boiled eggs with toast"


def test_parse_meal_command_accepts_log_meal_prefix() -> None:
    assert _parse_meal_command("log meal: Test Dish") == "Test Dish"


def test_parse_meal_command_ignores_regular_text() -> None:
    assert _parse_meal_command("Hello there") is None


def test_log_meal_command_persists_event_and_profile(tmp_path: Path) -> None:
    app_store = SQLiteRepository(str(tmp_path / "chat-meals.db"))
    stores = build_app_stores(app_store)

    result = _log_meal_command(
        user_id="user-42",
        meal_text="Soft-boiled eggs with wholemeal toast",
        stores=stores,
    )

    assert "Soft-boiled eggs" in result["message"]
    assert len(stores.meals.list_validated_meal_events("user-42")) == 1
    assert len(stores.meals.list_nutrition_risk_profiles("user-42")) == 1
