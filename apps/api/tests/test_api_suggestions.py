from collections.abc import Generator
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from apps.api.dietary_api.main import create_app
from dietary_guardian.config.settings import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_suggestions_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
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


def test_suggestions_generate_from_report_persists_and_lists(sqlite_suggestions_env: None) -> None:
    client = TestClient(create_app())
    _login(client)
    _meal_upload(client)

    create = client.post(
        "/api/v1/suggestions/generate-from-report",
        json={"text": "HbA1c 7.1 LDL 4.2 systolic bp 150 diastolic bp 95"},
    )

    assert create.status_code == 200
    assert create.headers["x-request-id"]
    assert create.headers["x-correlation-id"]
    body = create.json()
    assert "suggestion" in body
    suggestion = body["suggestion"]
    assert suggestion["suggestion_id"]
    assert suggestion["disclaimer"]
    assert suggestion["safety"]["decision"] == "allow"
    assert suggestion["report_parse"]["readings"]
    assert suggestion["recommendation"]["localized_advice"]
    assert suggestion["workflow"]["request_id"] == create.headers["x-request-id"]
    assert suggestion["workflow"]["correlation_id"] == create.headers["x-correlation-id"]
    assert "workflow" in suggestion

    listing = client.get("/api/v1/suggestions")
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) == 1
    assert items[0]["suggestion_id"] == suggestion["suggestion_id"]
    assert items[0]["recommendation"]["safe"] in {True, False}

    detail = client.get(f"/api/v1/suggestions/{suggestion['suggestion_id']}")
    assert detail.status_code == 200
    assert detail.json()["suggestion"]["suggestion_id"] == suggestion["suggestion_id"]


def test_suggestions_generate_from_report_requires_meal_record(sqlite_suggestions_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.post(
        "/api/v1/suggestions/generate-from-report",
        json={"text": "HbA1c 7.1 LDL 4.2"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "no meal records available"


def test_suggestions_endpoints_require_auth(sqlite_suggestions_env: None) -> None:
    client = TestClient(create_app())

    create = client.post("/api/v1/suggestions/generate-from-report", json={"text": "HbA1c 7.1"})
    list_resp = client.get("/api/v1/suggestions")

    assert create.status_code == 401
    assert list_resp.status_code == 401


def test_suggestions_red_flag_text_escalates_without_meal(sqlite_suggestions_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.post(
        "/api/v1/suggestions/generate-from-report",
        json={"text": "I have severe chest pain and trouble breathing right now"},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.headers["x-correlation-id"]
    suggestion = response.json()["suggestion"]
    assert suggestion["safety"]["decision"] == "escalate"
    assert suggestion["safety"]["reasons"]
    assert "urgent medical care" in suggestion["recommendation"]["rationale"].lower()
    assert suggestion["recommendation"]["safe"] is False


def test_suggestions_list_household_scope_includes_member_records(sqlite_suggestions_env: None) -> None:
    app = create_app()
    member_client = TestClient(app)
    helper_client = TestClient(app)

    _login(member_client, "member@example.com", "member-pass")
    _login(helper_client, "helper@example.com", "helper-pass")

    created = member_client.post("/api/v1/households", json={"name": "Family Circle"})
    assert created.status_code == 200
    household_id = created.json()["household"]["household_id"]
    invite = member_client.post(f"/api/v1/households/{household_id}/invites")
    assert invite.status_code == 200
    code = invite.json()["invite"]["code"]
    joined = helper_client.post("/api/v1/households/join", json={"code": code})
    assert joined.status_code == 200

    _meal_upload(member_client, color=(120, 210, 90))
    _meal_upload(helper_client, color=(95, 120, 210))
    member_create = member_client.post("/api/v1/suggestions/generate-from-report", json={"text": "HbA1c 6.8 LDL 3.2"})
    helper_create = helper_client.post("/api/v1/suggestions/generate-from-report", json={"text": "HbA1c 7.5 LDL 4.2"})
    assert member_create.status_code == 200
    assert helper_create.status_code == 200
    helper_suggestion_id = helper_create.json()["suggestion"]["suggestion_id"]

    set_active = member_client.patch("/api/v1/households/active", json={"household_id": household_id})
    assert set_active.status_code == 200

    household_list = member_client.get("/api/v1/suggestions?scope=household")
    assert household_list.status_code == 200
    items = household_list.json()["items"]
    authors = {item["source_user_id"] for item in items}
    assert {"user_001", "care_001"}.issubset(authors)

    detail = member_client.get(f"/api/v1/suggestions/{helper_suggestion_id}?scope=household")
    assert detail.status_code == 200
    assert detail.json()["suggestion"]["source_user_id"] == "care_001"
