from datetime import datetime, timedelta, timezone

from dietary_guardian.config.settings import Settings

from apps.api.dietary_api.auth import InMemoryAuthStore


def test_get_session_drops_expired_sessions() -> None:
    settings = Settings(llm_provider="test", auth_session_ttl_seconds=1)
    store = InMemoryAuthStore(settings)
    user = store.authenticate("member@example.com", "member-pass")
    assert user is not None
    session = store.create_session(user)
    session_id = str(session["session_id"])
    session["issued_at"] = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()

    looked_up = store.get_session(session_id)

    assert looked_up is None
    assert store.get_session(session_id) is None


def test_in_memory_store_honors_configured_demo_passwords() -> None:
    settings = Settings(
        llm_provider="test",
        auth_demo_member_password="member-custom-pass",
    )
    store = InMemoryAuthStore(settings)

    assert store.authenticate("member@example.com", "member-pass") is None
    assert store.authenticate("member@example.com", "member-custom-pass") is not None
