"""Module for test api medications."""

from collections.abc import Generator
from typing import Any, cast

import pytest
from apps.api.carepilot_api.main import create_app
from fastapi.testclient import TestClient

from care_pilot.agent.runtime.inference_engine import InferenceEngine
from care_pilot.agent.runtime.inference_types import InferenceResponse, ProviderMetadata
from care_pilot.config.app import get_settings
from care_pilot.features.medications.intake.models import (
    LLMNormalizedMedicationInstruction,
    MedicationParseOutput,
    NormalizedMedicationInstruction,
)


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_medications_env(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    monkeypatch.setenv("LLM_PROVIDER", "test")

    async def mock_infer(self, request: Any) -> InferenceResponse:
        if "Metformin" in str(request.payload.get("prompt", "")):
            instr = LLMNormalizedMedicationInstruction(
                medication_name_raw="Metformin 500mg",
                medication_name_canonical="metformin",
                dosage_text="1 tablet",
                timing_type="pre_meal",
                frequency_type="times_per_day",
                frequency_times_per_day=2,
                confidence=0.95,
                ambiguities=[],
            )
        elif "Amlodipine" in str(request.payload.get("prompt", "")):
            instr = LLMNormalizedMedicationInstruction(
                medication_name_raw="Amlodipine 5mg",
                medication_name_canonical="amlodipine",
                dosage_text="1 tablet",
                timing_type="fixed_time",
                frequency_type="fixed_time",
                fixed_time="08:00",
                confidence=0.95,
                ambiguities=[],
            )
        else:
            # Ambiguous case
            instr = LLMNormalizedMedicationInstruction(
                medication_name_raw="some tablets",
                dosage_text="",
                confidence=0.3,
                ambiguities=["could not determine dosage"],
            )

        instructions = cast(list[NormalizedMedicationInstruction], [instr])
        conf = float(instr.confidence) if instr.confidence is not None else 0.0
        output = MedicationParseOutput(
            instructions=instructions,
            confidence_score=0.95 if conf > 0.5 else 0.3,
            warnings=[],
        )
        return InferenceResponse(
            request_id=request.request_id,
            structured_output=output,
            confidence=output.confidence_score,
            latency_ms=10.0,
            provider_metadata=ProviderMetadata(
                provider="test", model="test-model", endpoint="test"
            ),
        )

    monkeypatch.setattr(InferenceEngine, "infer", mock_infer)

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


def test_medication_regimen_crud_and_adherence_metrics(
    sqlite_medications_env: None,
) -> None:
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


def test_reminder_generation_uses_persisted_regimens(
    sqlite_medications_env: None,
) -> None:
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


def test_medication_text_intake_previews_then_confirms_regimens_and_today_reminders(
    sqlite_medications_env: None,
) -> None:
    client = TestClient(create_app())
    _login(client)

    preview = client.post(
        "/api/v1/medications/intake/text",
        json={"instructions_text": "Metformin 500mg 1 tablet twice daily before meals for 5 days"},
    )

    assert preview.status_code == 200
    body = preview.json()
    assert body["draft_id"]
    assert body["regimens"] == []
    assert body["reminders"] == []
    assert body["scheduled_notifications"] == []
    assert body["source"]["source_type"] == "plain_text"
    assert (
        body["source"]["extracted_text"]
        == "Metformin 500mg 1 tablet twice daily before meals for 5 days"
    )
    assert body["normalized_instructions"]

    confirmed = client.post(
        "/api/v1/medications/intake/confirm",
        json={"draft_id": body["draft_id"]},
    )
    assert confirmed.status_code == 200
    confirmed_body = confirmed.json()
    assert any(item["medication_name"] == "Metformin" for item in confirmed_body["regimens"])
    assert any(item["medication_name"] == "Metformin" for item in confirmed_body["reminders"])
    assert confirmed_body["scheduled_notifications"]


def test_medication_text_intake_rejects_ambiguous_instructions_by_default(
    sqlite_medications_env: None,
) -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.post(
        "/api/v1/medications/intake/text",
        json={"instructions_text": "Please remind me about my tablets"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "medications.intake_review_required"


def test_medication_text_intake_allows_review_mode_for_ambiguous_instructions(
    sqlite_medications_env: None,
) -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.post(
        "/api/v1/medications/intake/text",
        json={
            "instructions_text": "Please remind me about my tablets",
            "allow_ambiguous": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["draft_id"]
    assert body["normalized_instructions"][0]["ambiguities"]
    assert body["regimens"] == []
    assert body["reminders"] == []


def test_medication_upload_intake_extracts_pdf_and_confirms_regimen(
    sqlite_medications_env: None,
) -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.post(
        "/api/v1/medications/intake/upload",
        files={
            "file": (
                "prescription.pdf",
                b"Amlodipine 5mg 1 tablet every morning",
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

    confirmed = client.post(
        "/api/v1/medications/intake/confirm",
        json={"draft_id": body["draft_id"]},
    )
    assert confirmed.status_code == 200
    assert any(item["medication_name"] == "Amlodipine" for item in confirmed.json()["regimens"])


def test_confirming_medication_reminder_records_adherence_event(
    sqlite_medications_env: None,
) -> None:
    client = TestClient(create_app())
    _login(client)

    preview = client.post(
        "/api/v1/medications/intake/text",
        json={"instructions_text": "Amlodipine 5mg every morning"},
    )
    assert preview.status_code == 200
    intake = client.post(
        "/api/v1/medications/intake/confirm",
        json={"draft_id": preview.json()["draft_id"]},
    )
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


def test_repeated_confirm_reuses_existing_regimen_and_reminders(
    sqlite_medications_env: None,
) -> None:
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

    first = client.post(
        "/api/v1/medications/intake/confirm",
        json={"draft_id": first_preview.json()["draft_id"]},
    )
    second = client.post(
        "/api/v1/medications/intake/confirm",
        json={"draft_id": second_preview.json()["draft_id"]},
    )

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

    response = client.post(
        "/api/v1/medications/intake/confirm",
        json={"draft_id": "missing-draft"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "medications.intake_draft_not_found"


def test_confirm_rejects_ambiguous_draft(sqlite_medications_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    preview = client.post(
        "/api/v1/medications/intake/text",
        json={
            "instructions_text": "Take some tablets",
            "allow_ambiguous": True,
        },
    )
    assert preview.status_code == 200
    draft_id = preview.json()["draft_id"]

    confirm = client.post("/api/v1/medications/intake/confirm", json={"draft_id": draft_id})
    assert confirm.status_code == 422
    assert confirm.json()["error"]["code"] == "medications.intake_review_required"


def test_editing_draft_updates_confirmed_regimen(
    sqlite_medications_env: None,
) -> None:
    client = TestClient(create_app())
    _login(client)

    preview = client.post(
        "/api/v1/medications/intake/text",
        json={"instructions_text": "Amlodipine 5mg every morning"},
    )
    assert preview.status_code == 200
    draft = preview.json()

    updated = client.patch(
        f"/api/v1/medications/intake/drafts/{draft['draft_id']}/instructions/0",
        json={
            "medication_name_raw": "Losartan",
            "medication_name_canonical": "losartan",
            "dosage_text": "50mg",
            "timing_type": "fixed_time",
            "frequency_type": "fixed_time",
            "frequency_times_per_day": 1,
            "offset_minutes": 0,
            "slot_scope": [],
            "fixed_time": "09:00",
            "time_rules": [{"kind": "fixed_time", "time_local": "09:00"}],
            "duration_days": None,
            "start_date": "2026-03-15",
            "end_date": None,
            "confidence": 1.0,
            "ambiguities": [],
        },
    )

    assert updated.status_code == 200
    confirm = client.post(
        "/api/v1/medications/intake/confirm",
        json={"draft_id": draft["draft_id"]},
    )
    assert confirm.status_code == 200
    assert confirm.json()["regimens"][0]["medication_name"] == "Losartan"
    assert confirm.json()["regimens"][0]["dosage_text"] == "50mg"


def test_deleting_draft_instruction_removes_it_from_confirmation(
    sqlite_medications_env: None,
) -> None:
    client = TestClient(create_app())
    _login(client)

    preview = client.post(
        "/api/v1/medications/intake/text",
        json={
            "instructions_text": "Amlodipine 5mg every morning; Metformin 500mg twice daily before meals"
        },
    )
    assert preview.status_code == 200
    draft = preview.json()
    assert len(draft["normalized_instructions"]) == 2

    deleted = client.delete(f"/api/v1/medications/intake/drafts/{draft['draft_id']}/instructions/0")
    assert deleted.status_code == 200
    assert len(deleted.json()["normalized_instructions"]) == 1

    confirm = client.post(
        "/api/v1/medications/intake/confirm",
        json={"draft_id": draft["draft_id"]},
    )
    assert confirm.status_code == 200
    assert len(confirm.json()["regimens"]) == 1


def test_canceling_draft_prevents_confirmation(
    sqlite_medications_env: None,
) -> None:
    client = TestClient(create_app())
    _login(client)

    preview = client.post(
        "/api/v1/medications/intake/text",
        json={"instructions_text": "Amlodipine 5mg every morning"},
    )
    assert preview.status_code == 200
    draft_id = preview.json()["draft_id"]

    cancelled = client.delete(f"/api/v1/medications/intake/drafts/{draft_id}")
    assert cancelled.status_code == 200
    assert cancelled.json()["ok"] is True

    confirm = client.post("/api/v1/medications/intake/confirm", json={"draft_id": draft_id})
    assert confirm.status_code == 404
    assert confirm.json()["error"]["code"] == "medications.intake_draft_not_found"


def test_duplicate_manual_regimen_create_returns_conflict(
    sqlite_medications_env: None,
) -> None:
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
