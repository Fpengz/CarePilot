from fastapi.testclient import TestClient

from apps.api.dietary_api.main import create_app


def _login(client: TestClient, email: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_generate_list_and_confirm_reminders_flow() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    generated = client.post("/api/v1/reminders/generate")
    assert generated.status_code == 200
    generated_body = generated.json()
    assert generated_body["reminders"]
    event_id = generated_body["reminders"][0]["id"]

    listed = client.get("/api/v1/reminders")
    assert listed.status_code == 200
    assert listed.json()["metrics"]["reminders_sent"] >= 1

    confirmed = client.post(f"/api/v1/reminders/{event_id}/confirm", json={"confirmed": True})
    assert confirmed.status_code == 200
    assert confirmed.json()["event"]["status"] == "acknowledged"

    listed_after = client.get("/api/v1/reminders")
    assert listed_after.status_code == 200
    assert listed_after.json()["metrics"]["meal_confirmed_yes"] >= 1
