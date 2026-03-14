"""Module for test api medications."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from apps.api.dietary_api.main import create_app
from fastapi.testclient import TestClient

from dietary_guardian.config.app import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_medications_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient, email: str = "member@example.com", password: str = "member-pass") -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_medication_regimen_crud_and_adherence_metrics(sqlite_medications_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    created = client.post(
        "/api/v1/medications/regimens",
        json={
            "medication_name": "Lisinopril",
            "dosage_text": "10mg",
            "timing_type": "fixed_time",
            "fixed_time": "09:00",
            "offset_minutes": 0,
            "slot_scope": [],
            "max_daily_doses": 1,
            "active": True,
        },
    )
    assert created.status_code == 200
    regimen_id = created.json()["regimen"]["id"]

    listed = client.get("/api/v1/medications/regimens")
    assert listed.status_code == 200
    assert any(item["id"] == regimen_id for item in listed.json()["items"])

    updated = client.patch(
        f"/api/v1/medications/regimens/{regimen_id}",
        json={"active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["regimen"]["active"] is False

    adherence = client.post(
        "/api/v1/medications/adherence-events",
        json={
            "regimen_id": regimen_id,
            "status": "taken",
            "scheduled_at": "2026-03-01T09:00:00+00:00",
            "taken_at": "2026-03-01T09:05:00+00:00",
            "source": "manual",
        },
    )
    assert adherence.status_code == 200

    metrics = client.get("/api/v1/medications/adherence-metrics?from=2026-03-01&to=2026-03-02")
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["totals"]["events"] == 1
    assert body["totals"]["taken"] == 1
    assert body["totals"]["adherence_rate"] == 1.0


def test_reminder_generation_uses_persisted_regimens(sqlite_medications_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    created = client.post(
        "/api/v1/medications/regimens",
        json={
            "medication_name": "Atorvastatin",
            "dosage_text": "20mg",
            "timing_type": "fixed_time",
            "fixed_time": "22:00",
            "offset_minutes": 0,
            "slot_scope": [],
            "max_daily_doses": 1,
            "active": True,
        },
    )
    assert created.status_code == 200

    generated = client.post("/api/v1/reminders/generate")
    assert generated.status_code == 200
    reminders = generated.json()["reminders"]
    assert any(item["medication_name"] == "Atorvastatin" for item in reminders)


def test_medication_text_intake_previews_then_confirms_regimens_and_today_reminders(sqlite_medications_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    preview = client.post(
        "/api/v1/medications/intake/text",
        json={"instructions_text": "Take Metformin 500mg twice daily before meals for 5 days"},
    )

    assert preview.status_code == 200
    body = preview.json()
    assert body["draft_id"]
    assert body["regimens"] == []
    assert body["reminders"] == []
    assert body["scheduled_notifications"] == []
    assert body["source"]["source_type"] == "plain_text"
    assert body["source"]["extracted_text"] == "Take Metformin 500mg twice daily before meals for 5 days"
    assert body["normalized_instructions"]

    confirmed = client.post("/api/v1/medications/intake/confirm", json={"draft_id": body["draft_id"]})
    assert confirmed.status_code == 200
    confirmed_body = confirmed.json()
    assert any(item["medication_name"] == "Metformin" for item in confirmed_body["regimens"])
    assert any(item["medication_name"] == "Metformin" for item in confirmed_body["reminders"])
    assert confirmed_body["scheduled_notifications"]


def test_medication_text_intake_rejects_ambiguous_instructions_by_default(sqlite_medications_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.post(
        "/api/v1/medications/intake/text",
        json={"instructions_text": "Please remind me about my tablets"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "medications.intake_review_required"


def test_medication_text_intake_allows_review_mode_for_ambiguous_instructions(sqlite_medications_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.post(
        "/api/v1/medications/intake/text",
        json={"instructions_text": "Please remind me about my tablets", "allow_ambiguous": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["draft_id"]
    assert body["normalized_instructions"][0]["ambiguities"]
    assert body["regimens"] == []
    assert body["reminders"] == []


def test_medication_upload_intake_extracts_pdf_and_confirms_regimen(sqlite_medications_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.post(
        "/api/v1/medications/intake/upload",
        files={
            "file": (
                "prescription.pdf",
                b"Take Amlodipine 5mg every morning",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"]["source_type"] == "upload"
    assert body["source"]["filename"] == "prescription.pdf"
    assert body["source"]["mime_type"] == "application/pdf"
    assert body["draft_id"]
    assert body["regimens"] == []

    confirmed = client.post("/api/v1/medications/intake/confirm", json={"draft_id": body["draft_id"]})
    assert confirmed.status_code == 200
    assert any(item["medication_name"] == "Amlodipine" for item in confirmed.json()["regimens"])


def test_confirming_medication_reminder_records_adherence_event(sqlite_medications_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    preview = client.post(
        "/api/v1/medications/intake/text",
        json={"instructions_text": "Amlodipine 5mg every morning"},
    )
    assert preview.status_code == 200
    intake = client.post("/api/v1/medications/intake/confirm", json={"draft_id": preview.json()["draft_id"]})
    assert intake.status_code == 200
    regimen_id = intake.json()["regimens"][0]["id"]
    reminder_id = intake.json()["reminders"][0]["id"]

    confirmed = client.post(f"/api/v1/reminders/{reminder_id}/confirm", json={"confirmed": True})
    assert confirmed.status_code == 200

    metrics = client.get("/api/v1/medications/adherence-metrics")
    assert metrics.status_code == 200
    events = metrics.json()["events"]
    assert len(events) == 1
    assert events[0]["regimen_id"] == regimen_id
    assert events[0]["reminder_id"] == reminder_id
    assert events[0]["status"] == "taken"
    assert events[0]["source"] == "reminder_confirm"


def test_repeated_confirm_reuses_existing_regimen_and_reminders(sqlite_medications_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    first_preview = client.post(
        "/api/v1/medications/intake/text",
        json={"instructions_text": "Amlodipine 5mg every morning"},
    )
    second_preview = client.post(
        "/api/v1/medications/intake/text",
        json={"instructions_text": "Amlodipine 5mg every morning"},
    )

    first = client.post("/api/v1/medications/intake/confirm", json={"draft_id": first_preview.json()["draft_id"]})
    second = client.post("/api/v1/medications/intake/confirm", json={"draft_id": second_preview.json()["draft_id"]})

    assert first_preview.status_code == 200
    assert second_preview.status_code == 200
    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert first_body["regimens"][0]["id"] == second_body["regimens"][0]["id"]
    assert first_body["reminders"][0]["id"] == second_body["reminders"][0]["id"]


def test_confirm_requires_valid_draft(sqlite_medications_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.post("/api/v1/medications/intake/confirm", json={"draft_id": "missing-draft"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "medications.intake_draft_not_found"


def test_duplicate_manual_regimen_create_returns_conflict(sqlite_medications_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    payload = {
        "medication_name": "Amlodipine",
        "dosage_text": "5mg",
        "timing_type": "fixed_time",
        "fixed_time": "08:00",
        "offset_minutes": 0,
        "slot_scope": [],
        "max_daily_doses": 1,
        "active": True,
    }

    first = client.post("/api/v1/medications/regimens", json=payload)
    second = client.post("/api/v1/medications/regimens", json=payload)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "medications.duplicate_regimen"
