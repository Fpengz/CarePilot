from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from apps.api.dietary_api.main import create_app
from dietary_guardian.config.settings import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_household_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "app.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient, email: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_household_create_requires_auth(sqlite_household_env: None) -> None:
    client = TestClient(create_app())

    response = client.post("/api/v1/households", json={"name": "Family Circle"})

    assert response.status_code == 401


def test_household_create_and_get_current(sqlite_household_env: None) -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    created = client.post("/api/v1/households", json={"name": "Family Circle"})
    assert created.status_code == 200
    body = created.json()
    assert body["household"]["name"] == "Family Circle"
    assert body["members"][0]["role"] == "owner"
    household_id = body["household"]["household_id"]

    current = client.get("/api/v1/households/current")
    assert current.status_code == 200
    current_body = current.json()
    assert current_body["household"]["household_id"] == household_id
    assert current_body["members"][0]["user_id"] == "user_001"
    assert current_body["members"][0]["display_name"]


def test_household_owner_can_invite_and_other_user_can_join(sqlite_household_env: None) -> None:
    app = create_app()
    owner_client = TestClient(app)
    helper_client = TestClient(app)

    _login(owner_client, "member@example.com", "member-pass")
    create = owner_client.post("/api/v1/households", json={"name": "Family Circle"})
    assert create.status_code == 200
    household_id = create.json()["household"]["household_id"]

    invite = owner_client.post(f"/api/v1/households/{household_id}/invites")
    assert invite.status_code == 200
    code = invite.json()["invite"]["code"]
    assert code

    _login(helper_client, "helper@example.com", "helper-pass")
    join = helper_client.post("/api/v1/households/join", json={"code": code})
    assert join.status_code == 200
    assert join.json()["household"]["household_id"] == household_id

    members = owner_client.get(f"/api/v1/households/{household_id}/members")
    assert members.status_code == 200
    items = members.json()["members"]
    assert {item["user_id"] for item in items} == {"user_001", "care_001"}
    roles = {item["user_id"]: item["role"] for item in items}
    assert roles["user_001"] == "owner"
    assert roles["care_001"] == "member"


def test_non_owner_cannot_create_household_invite(sqlite_household_env: None) -> None:
    app = create_app()
    owner_client = TestClient(app)
    helper_client = TestClient(app)

    _login(owner_client, "member@example.com", "member-pass")
    created = owner_client.post("/api/v1/households", json={"name": "Family Circle"})
    assert created.status_code == 200
    household_id = created.json()["household"]["household_id"]

    _login(helper_client, "helper@example.com", "helper-pass")
    helper_join = helper_client.post(
        "/api/v1/households/join",
        json={"code": owner_client.post(f"/api/v1/households/{household_id}/invites").json()["invite"]["code"]},
    )
    assert helper_join.status_code == 200

    forbidden = helper_client.post(f"/api/v1/households/{household_id}/invites")
    assert forbidden.status_code == 403


def test_user_cannot_create_or_join_second_household(sqlite_household_env: None) -> None:
    app = create_app()
    member_client = TestClient(app)
    helper_client = TestClient(app)
    admin_client = TestClient(app)

    _login(member_client, "member@example.com", "member-pass")
    _login(helper_client, "helper@example.com", "helper-pass")
    _login(admin_client, "admin@example.com", "admin-pass")

    first = member_client.post("/api/v1/households", json={"name": "One"})
    assert first.status_code == 200
    create_again = member_client.post("/api/v1/households", json={"name": "Two"})
    assert create_again.status_code == 409

    admin_household = admin_client.post("/api/v1/households", json={"name": "Ops Home"})
    assert admin_household.status_code == 200
    admin_household_id = admin_household.json()["household"]["household_id"]
    invite = admin_client.post(f"/api/v1/households/{admin_household_id}/invites")
    assert invite.status_code == 200

    join = helper_client.post("/api/v1/households/join", json={"code": invite.json()["invite"]["code"]})
    assert join.status_code == 200
    join_again = helper_client.post("/api/v1/households/join", json={"code": invite.json()["invite"]["code"]})
    assert join_again.status_code == 409


def test_household_owner_can_remove_member(sqlite_household_env: None) -> None:
    app = create_app()
    owner_client = TestClient(app)
    helper_client = TestClient(app)

    _login(owner_client, "member@example.com", "member-pass")
    _login(helper_client, "helper@example.com", "helper-pass")
    created = owner_client.post("/api/v1/households", json={"name": "Family Circle"})
    household_id = created.json()["household"]["household_id"]
    invite = owner_client.post(f"/api/v1/households/{household_id}/invites")
    code = invite.json()["invite"]["code"]
    assert helper_client.post("/api/v1/households/join", json={"code": code}).status_code == 200

    removed = owner_client.post(f"/api/v1/households/{household_id}/members/care_001/remove")

    assert removed.status_code == 200
    assert removed.json() == {"ok": True, "removed_user_id": "care_001"}
    members = owner_client.get(f"/api/v1/households/{household_id}/members")
    assert members.status_code == 200
    assert [item["user_id"] for item in members.json()["members"]] == ["user_001"]
    assert helper_client.get("/api/v1/households/current").json()["household"] is None


def test_non_owner_cannot_remove_household_member(sqlite_household_env: None) -> None:
    app = create_app()
    owner_client = TestClient(app)
    helper_client = TestClient(app)
    admin_client = TestClient(app)

    _login(owner_client, "member@example.com", "member-pass")
    _login(helper_client, "helper@example.com", "helper-pass")
    _login(admin_client, "admin@example.com", "admin-pass")
    household_id = owner_client.post("/api/v1/households", json={"name": "Family Circle"}).json()["household"][
        "household_id"
    ]
    code = owner_client.post(f"/api/v1/households/{household_id}/invites").json()["invite"]["code"]
    assert helper_client.post("/api/v1/households/join", json={"code": code}).status_code == 200

    forbidden = helper_client.post(f"/api/v1/households/{household_id}/members/user_001/remove")
    not_member = admin_client.post(f"/api/v1/households/{household_id}/members/care_001/remove")

    assert forbidden.status_code == 403
    assert not_member.status_code == 404


def test_household_member_can_leave_but_owner_cannot_leave_v1(sqlite_household_env: None) -> None:
    app = create_app()
    owner_client = TestClient(app)
    helper_client = TestClient(app)

    _login(owner_client, "member@example.com", "member-pass")
    _login(helper_client, "helper@example.com", "helper-pass")
    household_id = owner_client.post("/api/v1/households", json={"name": "Family Circle"}).json()["household"][
        "household_id"
    ]
    code = owner_client.post(f"/api/v1/households/{household_id}/invites").json()["invite"]["code"]
    assert helper_client.post("/api/v1/households/join", json={"code": code}).status_code == 200

    leave = helper_client.post(f"/api/v1/households/{household_id}/leave")
    owner_leave = owner_client.post(f"/api/v1/households/{household_id}/leave")

    assert leave.status_code == 200
    assert leave.json() == {"ok": True, "left_household_id": household_id}
    assert helper_client.get("/api/v1/households/current").json()["household"] is None
    assert owner_leave.status_code == 403


def test_household_owner_can_rename_household(sqlite_household_env: None) -> None:
    app = create_app()
    owner_client = TestClient(app)
    helper_client = TestClient(app)

    _login(owner_client, "member@example.com", "member-pass")
    _login(helper_client, "helper@example.com", "helper-pass")
    created = owner_client.post("/api/v1/households", json={"name": "Family Circle"})
    household_id = created.json()["household"]["household_id"]
    code = owner_client.post(f"/api/v1/households/{household_id}/invites").json()["invite"]["code"]
    assert helper_client.post("/api/v1/households/join", json={"code": code}).status_code == 200

    renamed = owner_client.patch(f"/api/v1/households/{household_id}", json={"name": "Wellness Crew"})
    forbidden = helper_client.patch(f"/api/v1/households/{household_id}", json={"name": "Nope"})

    assert renamed.status_code == 200
    assert renamed.json()["household"]["name"] == "Wellness Crew"
    assert helper_client.get("/api/v1/households/current").json()["household"]["name"] == "Wellness Crew"
    assert forbidden.status_code == 403


def test_household_active_selection_is_session_scoped(sqlite_household_env: None) -> None:
    app = create_app()
    client_a = TestClient(app)
    client_b = TestClient(app)

    _login(client_a, "member@example.com", "member-pass")
    _login(client_b, "member@example.com", "member-pass")
    household_id = client_a.post("/api/v1/households", json={"name": "Family Circle"}).json()["household"][
        "household_id"
    ]

    set_active = client_a.patch("/api/v1/households/active", json={"household_id": household_id})
    current_a = client_a.get("/api/v1/households/current")
    current_b = client_b.get("/api/v1/households/current")
    clear_active = client_a.patch("/api/v1/households/active", json={"household_id": None})

    assert set_active.status_code == 200
    assert set_active.json() == {"ok": True, "active_household_id": household_id}
    assert current_a.status_code == 200
    assert current_a.json()["active_household_id"] == household_id
    assert current_b.status_code == 200
    assert current_b.json()["active_household_id"] is None
    assert clear_active.status_code == 200
    assert clear_active.json() == {"ok": True, "active_household_id": None}


def test_household_active_selection_requires_membership(sqlite_household_env: None) -> None:
    app = create_app()
    member_client = TestClient(app)
    admin_client = TestClient(app)
    _login(member_client, "member@example.com", "member-pass")
    _login(admin_client, "admin@example.com", "admin-pass")
    member_household_id = member_client.post("/api/v1/households", json={"name": "Family Circle"}).json()["household"][
        "household_id"
    ]

    response = admin_client.patch("/api/v1/households/active", json={"household_id": member_household_id})

    assert response.status_code == 404
