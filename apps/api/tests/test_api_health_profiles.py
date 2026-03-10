from collections.abc import Generator
from io import BytesIO

import pytest
from apps.api.dietary_api.main import create_app
from fastapi.testclient import TestClient
from PIL import Image

from dietary_guardian.config.settings import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_health_profile_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient, email: str = "member@example.com", password: str = "member-pass") -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def _meal_upload(client: TestClient, *, color: tuple[int, int, int] = (120, 210, 90)) -> None:
    img = Image.new("RGB", (64, 64), color=color)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", buf.getvalue(), "image/jpeg")},
        data={"runtime_mode": "local", "provider": "test"},
    )
    assert response.status_code == 200


def test_health_profile_patch_persists_across_requests(sqlite_health_profile_env: None) -> None:
    app = create_app()
    client = TestClient(app)
    _login(client)

    patch = client.patch(
        "/api/v1/profile/health",
        json={
            "age": 54,
            "locale": "en-SG",
            "daily_sodium_limit_mg": 1600,
            "daily_sugar_limit_g": 24,
            "daily_protein_target_g": 72,
            "daily_fiber_target_g": 28,
            "conditions": [{"name": "Type 2 Diabetes", "severity": "High"}],
            "medications": [{"name": "Metformin", "dosage": "500mg", "contraindications": []}],
            "allergies": ["shellfish"],
            "nutrition_goals": ["lower_sugar", "lower_sodium"],
            "preferred_cuisines": ["teochew", "indian"],
            "disliked_ingredients": ["lard"],
            "budget_tier": "moderate",
        },
    )

    assert patch.status_code == 200
    body = patch.json()["profile"]
    assert body["locale"] == "en-SG"
    assert body["conditions"][0]["name"] == "Type 2 Diabetes"
    assert body["nutrition_goals"] == ["lower_sugar", "lower_sodium"]
    assert body["daily_protein_target_g"] == 72
    assert body["daily_fiber_target_g"] == 28
    assert body["completeness"]["state"] == "ready"
    assert body["completeness"]["missing_fields"] == []

    fetched = client.get("/api/v1/profile/health")
    assert fetched.status_code == 200
    fetched_body = fetched.json()["profile"]
    assert fetched_body["age"] == 54
    assert fetched_body["allergies"] == ["shellfish"]
    assert fetched_body["budget_tier"] == "moderate"
    assert fetched_body["daily_protein_target_g"] == 72
    assert fetched_body["daily_fiber_target_g"] == 28


def test_daily_suggestions_use_profile_history_and_snapshot(sqlite_health_profile_env: None) -> None:
    client = TestClient(create_app())
    _login(client)
    _meal_upload(client)
    assert (
        client.post(
            "/api/v1/reports/parse",
            json={"source": "pasted_text", "text": "HbA1c 7.4 LDL 4.1 systolic bp 148 diastolic bp 92"},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            "/api/v1/profile/health",
            json={
                "age": 54,
                "locale": "en-SG",
                "daily_sodium_limit_mg": 1500,
                "daily_sugar_limit_g": 24,
                "conditions": [{"name": "Type 2 Diabetes", "severity": "High"}],
                "medications": [{"name": "Metformin", "dosage": "500mg", "contraindications": []}],
                "allergies": ["shellfish"],
                "nutrition_goals": ["lower_sugar", "heart_health"],
                "preferred_cuisines": ["teochew"],
                "disliked_ingredients": ["lard", "shellfish"],
                "budget_tier": "moderate",
            },
        ).status_code
        == 200
    )

    response = client.get("/api/v1/suggestions/daily")

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["completeness"]["state"] == "ready"
    assert body["profile"]["locale"] == "en-SG"
    assert body["profile"]["fallback_mode"] is False
    assert body["bundle"]["locale"] == "en-SG"
    assert body["bundle"]["data_sources"]["meal_history_count"] >= 1
    assert body["bundle"]["data_sources"]["has_clinical_snapshot"] is True
    assert body["bundle"]["suggestions"]["breakfast"]["slot"] == "breakfast"
    assert body["bundle"]["suggestions"]["lunch"]["title"]
    assert body["bundle"]["suggestions"]["dinner"]["title"]
    combined_titles = " ".join(
        [
            body["bundle"]["suggestions"]["breakfast"]["title"].lower(),
            body["bundle"]["suggestions"]["lunch"]["title"].lower(),
            body["bundle"]["suggestions"]["dinner"]["title"].lower(),
        ]
    )
    assert "shellfish" not in combined_titles
    assert all("lard" not in reason.lower() for item in body["bundle"]["suggestions"].values() for reason in item["why_it_fits"])


def test_daily_suggestions_flag_incomplete_profile_with_fallback(sqlite_health_profile_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.get("/api/v1/suggestions/daily")

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["fallback_mode"] is True
    assert body["profile"]["completeness"]["state"] == "needs_profile"
    assert "conditions" in body["profile"]["completeness"]["missing_fields"]
    assert body["bundle"]["warnings"]
    assert body["bundle"]["suggestions"]["breakfast"]["confidence"] < 0.9


def test_health_profile_onboarding_defaults_patch_and_complete(sqlite_health_profile_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    initial = client.get("/api/v1/profile/health/onboarding")

    assert initial.status_code == 200
    initial_body = initial.json()
    assert initial_body["onboarding"]["current_step"] == "basic_identity"
    assert initial_body["onboarding"]["completed_steps"] == []
    assert initial_body["onboarding"]["is_complete"] is False
    assert [item["id"] for item in initial_body["steps"]] == [
        "basic_identity",
        "health_context",
        "nutrition_targets",
        "preferences",
        "review",
    ]

    patched = client.patch(
        "/api/v1/profile/health/onboarding",
        json={
            "step_id": "basic_identity",
            "profile": {
                "age": 54,
                "locale": "en-SG",
                "height_cm": 168,
                "weight_kg": 72,
            },
        },
    )

    assert patched.status_code == 200
    patched_body = patched.json()
    assert patched_body["onboarding"]["current_step"] == "health_context"
    assert patched_body["onboarding"]["completed_steps"] == ["basic_identity"]
    assert patched_body["profile"]["age"] == 54
    assert patched_body["profile"]["height_cm"] == 168.0

    completed = client.post("/api/v1/profile/health/onboarding/complete")

    assert completed.status_code == 200
    completed_body = completed.json()
    assert completed_body["onboarding"]["is_complete"] is True
    assert completed_body["onboarding"]["current_step"] == "review"
    assert set(completed_body["onboarding"]["completed_steps"]) == {
        "basic_identity",
        "health_context",
        "nutrition_targets",
        "preferences",
        "review",
    }
