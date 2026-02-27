from io import BytesIO
import logging
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from apps.api.dietary_api.main import create_app
from dietary_guardian.config.settings import get_settings
from dietary_guardian.models.meal import MealState, Nutrition, VisionResult
from dietary_guardian.models.meal_record import MealRecognitionRecord


def _jpeg_bytes() -> bytes:
    img = Image.new("RGB", (64, 64), color=(255, 0, 0))
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


def _jpeg_bytes_with_color(color: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (64, 64), color=color)
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


def _login(client: TestClient, email: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


def test_meal_analyze_requires_auth() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 401


def test_meal_analyze_returns_record_envelope_and_workflow() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"runtime_mode": "local", "provider": "test"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "vision_result" in body
    assert "meal_record" in body
    assert "summary" in body
    assert "output_envelope" in body
    assert "workflow" in body
    assert body["workflow"]["workflow_name"] == "meal_analysis"
    assert isinstance(body["summary"]["meal_name"], str)
    assert isinstance(body["summary"]["confidence"], float)
    assert body["summary"]["confidence"] >= 0.0
    assert isinstance(body["summary"]["estimated_calories"], (int, float))
    assert isinstance(body["summary"]["flags"], list)
    assert isinstance(body["summary"]["portion_size"], str)
    assert "needs_manual_review" in body["summary"]


def test_meal_analyze_rejects_empty_file_payload() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", b"", "image/jpeg")},
        data={"runtime_mode": "local", "provider": "test"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "empty upload"
    assert response.json()["error"]["code"] == "meal.empty_upload"


def test_meal_analyze_rejects_missing_content_type() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", _jpeg_bytes(), "")},
        data={"runtime_mode": "local", "provider": "test"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "unsupported image format"
    assert response.json()["error"]["code"] == "meal.unsupported_image_format"


def test_meal_analyze_rejects_duplicate_capture_with_domain_code() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")
    image = _jpeg_bytes()

    first = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", image, "image/jpeg")},
        data={"runtime_mode": "local", "provider": "test"},
    )
    duplicate = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", image, "image/jpeg")},
        data={"runtime_mode": "local", "provider": "test"},
    )

    assert first.status_code == 200
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "duplicate capture suppressed"
    assert duplicate.json()["error"]["code"] == "meal.duplicate_capture"


def test_meal_records_limit_query_truncates_response() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    for color in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]:
        response = client.post(
            "/api/v1/meal/analyze",
            files={"file": ("meal.jpg", _jpeg_bytes_with_color(color), "image/jpeg")},
            data={"runtime_mode": "local", "provider": "test"},
        )
        assert response.status_code == 200

    all_records = client.get("/api/v1/meal/records")
    limited = client.get("/api/v1/meal/records?limit=2")

    assert all_records.status_code == 200
    assert limited.status_code == 200
    assert len(all_records.json()["records"]) >= 3
    assert len(limited.json()["records"]) == 2
    assert "page" in limited.json()
    assert isinstance(limited.json()["page"], dict)


def test_meal_records_cursor_pagination_returns_next_page() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    for color in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]:
        response = client.post(
            "/api/v1/meal/analyze",
            files={"file": ("meal.jpg", _jpeg_bytes_with_color(color), "image/jpeg")},
            data={"runtime_mode": "local", "provider": "test"},
        )
        assert response.status_code == 200

    page_one = client.get("/api/v1/meal/records?limit=2")
    assert page_one.status_code == 200
    first_ids = [record["id"] for record in page_one.json()["records"]]
    next_cursor = page_one.json()["page"]["next_cursor"]
    assert next_cursor is not None

    page_two = client.get(f"/api/v1/meal/records?limit=2&cursor={next_cursor}")
    assert page_two.status_code == 200
    second_ids = [record["id"] for record in page_two.json()["records"]]
    assert second_ids
    assert set(first_ids).isdisjoint(second_ids)


def test_meal_records_rejects_invalid_cursor_with_standard_error() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    response = client.get("/api/v1/meal/records?cursor=bad-cursor")

    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == "invalid cursor"
    assert body["error"]["code"] == "meal.invalid_cursor"
    assert body["error"]["correlation_id"]


def test_meal_records_validation_error_uses_standard_error_shape() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    response = client.get("/api/v1/meal/records?limit=0")

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "request validation failed"
    assert body["error"]["code"] == "request.validation_error"
    assert isinstance(body["error"]["details"]["errors"], list)


def test_meal_analyze_uses_settings_provider_when_form_provider_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "vllm")
    _reset_settings_cache()
    captured: dict[str, str] = {}

    class _FakeHawkerVisionModule:
        def __init__(self, provider: str) -> None:
            captured["provider"] = provider

        async def analyze_and_record(self, *args, **kwargs):
            state = MealState(
                dish_name="Test Dish",
                confidence_score=0.9,
                identification_method="AI_Flash",
                ingredients=[],
                nutrition=Nutrition(
                    calories=100.0,
                    carbs_g=10.0,
                    sugar_g=2.0,
                    protein_g=5.0,
                    fat_g=3.0,
                    sodium_mg=200.0,
                ),
            )
            return (
                VisionResult(primary_state=state, raw_ai_output="ok"),
                MealRecognitionRecord(
                    id=str(uuid4()),
                    user_id="member_001",
                    captured_at=datetime.now(timezone.utc),
                    source="upload",
                    meal_state=state,
                ),
            )

    monkeypatch.setattr(
        "apps.api.dietary_api.services.meals.HawkerVisionModule",
        _FakeHawkerVisionModule,
    )

    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"runtime_mode": "local"},
    )

    assert response.status_code == 200
    assert captured["provider"] == "vllm"
    _reset_settings_cache()


def test_meal_analyze_logs_response_summary(caplog: pytest.LogCaptureFixture) -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")
    caplog.set_level(logging.INFO)

    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"runtime_mode": "local", "provider": "test"},
    )

    assert response.status_code == 200
    response_logs = [record.message for record in caplog.records if "hawker_vision_response_summary" in record.message]
    assert response_logs
    assert "destination=" in response_logs[-1]
