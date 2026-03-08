from datetime import datetime, timedelta, timezone

from dietary_guardian.config.settings import Settings
from dietary_guardian.infrastructure.auth.sqlite_store import SQLiteAuthStore


def test_sqlite_auth_store_persists_users_and_sessions_across_instances(tmp_path) -> None:
    db_path = tmp_path / "auth.db"
    settings = Settings(llm_provider="test")

    store_a = SQLiteAuthStore(settings=settings, db_path=str(db_path))
    created = store_a.create_user(
        email="persist@example.com",
        password="persist-pass",
        display_name="Persist User",
        profile_mode="caregiver",
    )
    assert created is not None
    session = store_a.create_session(created)

    store_b = SQLiteAuthStore(settings=settings, db_path=str(db_path))
    authed = store_b.authenticate("persist@example.com", "persist-pass")

    assert authed is not None
    assert authed.display_name == "Persist User"
    looked_up = store_b.get_session(str(session["session_id"]))
    assert looked_up is not None
    assert looked_up["email"] == "persist@example.com"
    assert looked_up["profile_mode"] == "caregiver"


def test_sqlite_auth_store_expires_sessions(tmp_path) -> None:
    db_path = tmp_path / "auth.db"
    settings = Settings(llm_provider="test", auth_session_ttl_seconds=1)
    store = SQLiteAuthStore(settings=settings, db_path=str(db_path))
    user = store.authenticate("member@example.com", "member-pass")
    assert user is not None
    session = store.create_session(user)
    session_id = str(session["session_id"])

    store._conn.execute(
        "UPDATE auth_sessions SET issued_at = ? WHERE session_id = ?",
        ((datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat(), session_id),
    )
    store._conn.commit()

    assert store.get_session(session_id) is None


def test_sqlite_auth_store_records_login_lockout_and_audit_events(tmp_path) -> None:
    db_path = tmp_path / "auth.db"
    settings = Settings(
        llm_provider="test",
        auth_login_max_failed_attempts=2,
        auth_login_lockout_seconds=60,
    )
    store = SQLiteAuthStore(settings=settings, db_path=str(db_path))

    assert store.record_login_failure("x@example.com") is False
    assert store.record_login_failure("x@example.com") is True
    assert store.is_login_locked("x@example.com") is True

    store.append_auth_audit_event(event_type="login_locked", email="x@example.com")
    items = store.list_auth_audit_events(limit=5)
    assert items
    assert items[0]["event_type"] == "login_locked"


def test_sqlite_auth_store_drops_session_with_invalid_scopes_json(tmp_path) -> None:
    db_path = tmp_path / "auth.db"
    settings = Settings(llm_provider="test")
    store = SQLiteAuthStore(settings=settings, db_path=str(db_path))
    user = store.authenticate("member@example.com", "member-pass")
    assert user is not None
    session = store.create_session(user)
    session_id = str(session["session_id"])

    store._conn.execute(
        "UPDATE auth_sessions SET scopes_json = ? WHERE session_id = ?",
        ("", session_id),
    )
    store._conn.commit()

    assert store.get_session(session_id) is None
    row = store._conn.execute(
        "SELECT session_id FROM auth_sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    assert row is None


def test_sqlite_auth_store_can_disable_demo_user_seeding(tmp_path) -> None:
    db_path = tmp_path / "auth.db"
    settings = Settings(llm_provider="test", auth_seed_demo_users=False)

    store = SQLiteAuthStore(settings=settings, db_path=str(db_path))

    assert store.authenticate("member@example.com", "member-pass") is None
