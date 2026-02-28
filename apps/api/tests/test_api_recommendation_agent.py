from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from apps.api.dietary_api.main import create_app
from dietary_guardian.config.settings import get_settings
from dietary_guardian.models.meal import Ingredient, MealState, Nutrition
from dietary_guardian.models.meal_record import MealRecognitionRecord


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_agent_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient, email: str = "member@example.com", password: str = "member-pass") -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def _seed_profile(client: TestClient) -> None:
    response = client.patch(
        "/api/v1/profile/health",
        json={
            "age": 54,
            "locale": "en-SG",
            "height_cm": 168,
            "weight_kg": 79,
            "daily_sodium_limit_mg": 1500,
            "daily_sugar_limit_g": 24,
            "target_calories_per_day": 1850,
            "macro_focus": ["higher_protein", "lower_sugar"],
            "conditions": [{"name": "Type 2 Diabetes", "severity": "High"}],
            "medications": [{"name": "Metformin", "dosage": "500mg", "contraindications": []}],
            "allergies": ["shellfish"],
            "nutrition_goals": ["lower_sugar", "heart_health"],
            "preferred_cuisines": ["teochew", "indian"],
            "disliked_ingredients": ["lard"],
            "budget_tier": "moderate",
        },
    )
    assert response.status_code == 200


def _seed_meal_history(app, *, user_id: str = "user_001") -> None:
    repo = app.state.ctx.repository
    now = datetime.now(timezone.utc)
    seeded = [
        (
            "breakfast",
            "Plain thosai with dhal",
            Nutrition(calories=320, carbs_g=48, sugar_g=4, protein_g=9, fat_g=8, sodium_mg=380, fiber_g=5),
            ["lentils", "rice"],
        ),
        (
            "lunch",
            "Laksa",
            Nutrition(calories=690, carbs_g=62, sugar_g=7, protein_g=21, fat_g=34, sodium_mg=1650, fiber_g=3),
            ["noodles", "coconut", "shellfish"],
        ),
        (
            "dinner",
            "Char kway teow",
            Nutrition(calories=760, carbs_g=71, sugar_g=9, protein_g=22, fat_g=39, sodium_mg=1780, fiber_g=2),
            ["noodles", "lard", "soy sauce"],
        ),
        (
            "breakfast",
            "Soft-boiled eggs with wholemeal toast",
            Nutrition(calories=280, carbs_g=28, sugar_g=3, protein_g=14, fat_g=11, sodium_mg=340, fiber_g=4),
            ["eggs", "wholemeal bread"],
        ),
        (
            "lunch",
            "Sliced fish soup with rice",
            Nutrition(calories=430, carbs_g=46, sugar_g=2, protein_g=27, fat_g=11, sodium_mg=620, fiber_g=3),
            ["fish", "vegetables", "rice"],
        ),
        (
            "dinner",
            "Steamed chicken rice",
            Nutrition(calories=560, carbs_g=58, sugar_g=3, protein_g=26, fat_g=20, sodium_mg=980, fiber_g=2),
            ["chicken", "rice", "cucumber"],
        ),
        (
            "breakfast",
            "Kaya toast set",
            Nutrition(calories=420, carbs_g=52, sugar_g=18, protein_g=10, fat_g=16, sodium_mg=420, fiber_g=2),
            ["toast", "egg", "kaya"],
        ),
        (
            "lunch",
            "Mee rebus",
            Nutrition(calories=680, carbs_g=82, sugar_g=14, protein_g=18, fat_g=24, sodium_mg=1460, fiber_g=4),
            ["noodles", "gravy", "egg"],
        ),
        (
            "dinner",
            "Yong tau foo soup",
            Nutrition(calories=440, carbs_g=34, sugar_g=4, protein_g=26, fat_g=17, sodium_mg=740, fiber_g=5),
            ["tofu", "greens", "fish paste"],
        ),
        (
            "lunch",
            "Thunder tea rice",
            Nutrition(calories=470, carbs_g=49, sugar_g=3, protein_g=18, fat_g=17, sodium_mg=520, fiber_g=7),
            ["greens", "tofu", "rice"],
        ),
    ]
    for idx, (_, dish_name, nutrition, ingredients) in enumerate(seeded, start=1):
        record = MealRecognitionRecord(
            id=f"meal_{idx}",
            user_id=user_id,
            captured_at=now - timedelta(days=(10 - idx), hours=idx % 3),
            source="seeded",
            meal_state=MealState(
                dish_name=dish_name,
                confidence_score=0.99,
                identification_method="User_Manual",
                ingredients=[Ingredient(name=name) for name in ingredients],
                nutrition=nutrition,
            ),
        )
        repo.save_meal_record(record)


def _seed_snapshot(client: TestClient) -> None:
    response = client.post(
        "/api/v1/reports/parse",
        json={"source": "pasted_text", "text": "HbA1c 7.3 LDL 4.0 systolic bp 148 diastolic bp 92"},
    )
    assert response.status_code == 200


def test_daily_agent_returns_typed_recommendations_and_substitutions(sqlite_agent_env: None) -> None:
    app = create_app()
    client = TestClient(app)
    _login(client)
    _seed_profile(client)
    _seed_meal_history(app)
    _seed_snapshot(client)

    response = client.get("/api/v1/recommendations/daily-agent")

    assert response.status_code == 200
    body = response.json()
    assert body["fallback_mode"] is True
    assert body["profile_state"]["bmi"] > 25
    assert body["temporal_context"]["meal_history_count"] == 10
    assert body["data_sources"]["interaction_count"] == 0
    assert {"breakfast", "lunch", "dinner"}.issubset(body["recommendations"].keys())
    assert body["substitutions"]["source_meal"]["meal_id"] == "meal_10"
    assert body["substitutions"]["alternatives"]
    assert all("shellfish" not in item["title"].lower() for item in body["recommendations"].values())
    assert all("lard" not in item["title"].lower() for item in body["recommendations"].values())
    assert body["constraints_applied"]
    assert body["workflow"]["workflow_name"] == "daily_recommendation_agent"


def test_daily_agent_handles_empty_meal_history_with_fallback(sqlite_agent_env: None) -> None:
    client = TestClient(create_app())
    _login(client)
    _seed_profile(client)

    response = client.get("/api/v1/recommendations/daily-agent")

    assert response.status_code == 200
    body = response.json()
    assert body["fallback_mode"] is True
    assert body["temporal_context"]["meal_history_count"] == 0
    assert body["recommendations"]
    assert body["substitutions"] is None


def test_recommendation_interactions_refine_preferences_and_disable_fallback(sqlite_agent_env: None) -> None:
    app = create_app()
    client = TestClient(app)
    _login(client)
    _seed_profile(client)
    _seed_meal_history(app)
    _seed_snapshot(client)

    first = client.get("/api/v1/recommendations/daily-agent")
    assert first.status_code == 200
    breakfast = first.json()["recommendations"]["breakfast"]

    for index in range(5):
        interaction = client.post(
            "/api/v1/recommendations/interactions",
            json={
                "recommendation_id": first.json()["workflow"]["request_id"],
                "candidate_id": breakfast["candidate_id"],
                "event_type": "accepted",
                "slot": "breakfast",
                "metadata": {"sequence": index},
            },
        )
        assert interaction.status_code == 200

    second = client.get("/api/v1/recommendations/daily-agent")
    assert second.status_code == 200
    body = second.json()
    assert body["fallback_mode"] is False
    assert body["data_sources"]["interaction_count"] >= 5
    assert body["recommendations"]["breakfast"]["candidate_id"] == breakfast["candidate_id"]
    assert body["recommendations"]["breakfast"]["scores"]["preference_fit"] >= breakfast["scores"]["preference_fit"]


def test_substitution_endpoint_returns_healthier_low_deviation_swap(sqlite_agent_env: None) -> None:
    app = create_app()
    client = TestClient(app)
    _login(client)
    _seed_profile(client)
    _seed_meal_history(app)
    _seed_snapshot(client)

    response = client.post(
        "/api/v1/recommendations/substitutions",
        json={"source_meal_id": "meal_3", "limit": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_meal"]["meal_id"] == "meal_3"
    assert body["source_meal"]["title"] == "Char kway teow"
    assert len(body["alternatives"]) == 2
    assert body["alternatives"][0]["health_delta"]["sodium_mg"] < 0
    assert body["alternatives"][0]["health_delta"]["calories"] < 0
    assert body["alternatives"][0]["taste_distance"] <= 0.75
    assert "healthier" in body["alternatives"][0]["reasoning"].lower()
