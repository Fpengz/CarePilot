from __future__ import annotations

from collections.abc import Generator
from io import BytesIO
from sqlite3 import Row

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from apps.api.dietary_api.main import create_app
from dietary_guardian.config.settings import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_companion_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    monkeypatch.setenv("MEAL_ANALYZE_PROVIDER", "test")
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient, email: str = "member@example.com", password: str = "member-pass") -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def _meal_upload(client: TestClient) -> None:
    img = Image.new("RGB", (32, 32), color=(255, 200, 120))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", buf.getvalue(), "image/jpeg")},
        data={"provider": "test"},
    )
    assert response.status_code == 200


def _seed_companion_state(client: TestClient) -> None:
    _meal_upload(client)
    report = client.post(
        "/api/v1/reports/parse",
        json={"source": "pasted_text", "text": "HbA1c 7.3 LDL 4.4 systolic bp 146 diastolic bp 94"},
    )
    assert report.status_code == 200
    symptom = client.post(
        "/api/v1/symptoms/check-ins",
        json={
            "severity": 4,
            "symptom_codes": ["fatigue", "headache"],
            "free_text": "Feeling tired and headachy this week",
        },
    )
    assert symptom.status_code == 200
    reminders = client.post("/api/v1/reminders/generate")
    assert reminders.status_code == 200


def _set_subject_user_id(app_client: TestClient, *, session_id: str, subject_user_id: str) -> None:
    app = app_client.app
    assert isinstance(app, FastAPI)
    auth_store = app.state.ctx.auth_store
    with auth_store._lock:
        with auth_store._connect() as conn:
            row = conn.execute(
                "SELECT * FROM auth_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            assert isinstance(row, Row)
            conn.execute(
                """
                UPDATE auth_sessions
                SET subject_user_id = ?
                WHERE session_id = ?
                """,
                (subject_user_id, session_id),
            )
            conn.commit()


def test_companion_today_returns_priorities_and_snapshot(sqlite_companion_env: None) -> None:
    client = TestClient(create_app())
    _login(client)
    _seed_companion_state(client)

    response = client.get("/api/v1/companion/today")

    assert response.status_code == 200
    body = response.json()
    assert body["snapshot"]["meal_count"] >= 1
    assert body["snapshot"]["active_risk_flags"]
    assert body["care_plan"]["headline"]
    assert body["care_plan"]["recommended_actions"]
    assert body["engagement"]["recommended_mode"] in {"supportive", "accountability", "follow_up", "escalate"}


def test_companion_interaction_returns_digest_preview_and_impact(sqlite_companion_env: None) -> None:
    client = TestClient(create_app())
    _login(client)
    _seed_companion_state(client)

    response = client.post(
        "/api/v1/companion/interactions",
        json={
            "interaction_type": "check_in",
            "message": "I had another oily hawker lunch and I am worried about my sugar",
            "emotion_text": "I feel a bit discouraged and stressed about keeping up",
        },
        headers={"X-Request-ID": "req-companion-1", "X-Correlation-ID": "corr-companion-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["interaction"]["request_id"] == "req-companion-1"
    assert body["interaction"]["correlation_id"] == "corr-companion-1"
    assert body["care_plan"]["headline"]
    assert body["clinician_digest_preview"]["summary"]
    assert body["impact"]["tracked_metrics"]
    assert body["workflow"]["correlation_id"] == "corr-companion-1"


def test_companion_interaction_changes_by_interaction_type_and_includes_richer_guidance(
    sqlite_companion_env: None,
) -> None:
    client = TestClient(create_app())
    _login(client)
    _seed_companion_state(client)

    meal_review = client.post(
        "/api/v1/companion/interactions",
        json={
            "interaction_type": "meal_review",
            "message": "I had another oily hawker lunch. Give me one realistic food swap.",
            "emotion_text": "I feel discouraged about making better lunch choices.",
        },
    )
    adherence_follow_up = client.post(
        "/api/v1/companion/interactions",
        json={
            "interaction_type": "adherence_follow_up",
            "message": "I missed my meds again because I was rushing out the door.",
            "emotion_text": "I feel stressed and frustrated about missing medications.",
        },
    )

    assert meal_review.status_code == 200
    assert adherence_follow_up.status_code == 200

    meal_body = meal_review.json()
    adherence_body = adherence_follow_up.json()

    assert meal_body["care_plan"]["headline"] != adherence_body["care_plan"]["headline"]
    assert meal_body["care_plan"]["recommended_actions"] != adherence_body["care_plan"]["recommended_actions"]
    assert meal_body["care_plan"]["citations"]
    assert adherence_body["care_plan"]["citations"]
    assert meal_body["care_plan"]["policy_status"] in {"approved", "escalate", "adjusted"}
    assert adherence_body["care_plan"]["policy_status"] in {"approved", "escalate", "adjusted"}
    assert meal_body["clinician_digest_preview"]["time_window"]
    assert adherence_body["clinician_digest_preview"]["time_window"]
    assert meal_body["clinician_digest_preview"]["why_now"]
    assert adherence_body["clinician_digest_preview"]["why_now"]
    assert meal_body["impact"]["baseline_window"]
    assert adherence_body["impact"]["comparison_window"]
    assert "meal" in " ".join(meal_body["care_plan"]["recommended_actions"]).lower()
    assert (
        "medication" in " ".join(adherence_body["care_plan"]["recommended_actions"]).lower()
        or "reminder" in " ".join(adherence_body["care_plan"]["recommended_actions"]).lower()
    )


def test_clinician_digest_and_impact_summary_reflect_longitudinal_state(sqlite_companion_env: None) -> None:
    client = TestClient(create_app())
    _login(client)
    _seed_companion_state(client)

    digest = client.get("/api/v1/clinician/digest")
    impact = client.get("/api/v1/impact/summary")

    assert digest.status_code == 200
    digest_body = digest.json()
    assert digest_body["digest"]["what_changed"]
    assert digest_body["digest"]["recommended_actions"]
    assert digest_body["digest"]["risk_level"] in {"low", "medium", "high"}
    assert digest_body["digest"]["time_window"]
    assert digest_body["digest"]["priority"] in {"routine", "watch", "urgent"}
    assert digest_body["digest"]["why_now"]
    assert digest_body["digest"]["citations"]

    assert impact.status_code == 200
    impact_body = impact.json()
    assert impact_body["summary"]["tracked_metrics"]
    assert impact_body["summary"]["intervention_opportunities"] >= 1
    assert impact_body["summary"]["baseline_window"]
    assert impact_body["summary"]["comparison_window"]
    assert impact_body["summary"]["deltas"]
    assert impact_body["summary"]["interventions_measured"]


def test_companion_endpoints_use_subject_user_state_for_care_mode_sessions(sqlite_companion_env: None) -> None:
    app = create_app()
    member_client = TestClient(app)
    helper_client = TestClient(app)

    member_login = member_client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
    helper_login = helper_client.post("/api/v1/auth/login", json={"email": "helper@example.com", "password": "helper-pass"})
    assert member_login.status_code == 200
    assert helper_login.status_code == 200

    created = member_client.post("/api/v1/households", json={"name": "Family Circle"})
    assert created.status_code == 200
    household_id = created.json()["household"]["household_id"]
    invite = member_client.post(f"/api/v1/households/{household_id}/invites")
    assert invite.status_code == 200
    assert helper_client.post("/api/v1/households/join", json={"code": invite.json()["invite"]["code"]}).status_code == 200

    _seed_companion_state(member_client)
    _set_subject_user_id(
        helper_client,
        session_id=helper_login.json()["session"]["session_id"],
        subject_user_id="user_001",
    )

    today = helper_client.get("/api/v1/companion/today")
    interaction = helper_client.post(
        "/api/v1/companion/interactions",
        json={
            "interaction_type": "check_in",
            "message": "Help me decide on one realistic next step for today.",
            "emotion_text": "I feel discouraged about keeping up.",
        },
    )
    digest = helper_client.get("/api/v1/clinician/digest")
    impact = helper_client.get("/api/v1/impact/summary")

    assert today.status_code == 200
    assert interaction.status_code == 200
    assert digest.status_code == 200
    assert impact.status_code == 200

    today_body = today.json()
    interaction_body = interaction.json()
    digest_body = digest.json()
    impact_body = impact.json()

    assert today_body["snapshot"]["meal_count"] >= 1
    assert today_body["snapshot"]["symptom_count"] >= 1
    assert interaction_body["snapshot"]["meal_count"] >= 1
    assert interaction_body["snapshot"]["symptom_count"] >= 1
    assert digest_body["digest"]["what_changed"]
    assert impact_body["summary"]["tracked_metrics"]
