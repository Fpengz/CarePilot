"""
Tests for auth SQLModel persistence models.
"""

import json
from datetime import UTC, datetime, timedelta

from care_pilot.platform.persistence.models.auth_models import (
    AccountRole,
    AuthAuditEvent,
    AuthLoginFailure,
    AuthSession,
    AuthUser,
    ProfileMode,
)


def test_create_auth_user():
    """
    Tests the creation and attributes of an AuthUser instance.
    """
    user_id = "test_user_123"
    email = "test@example.com"
    display_name = "Test User"
    account_role: AccountRole = "member"
    profile_mode: ProfileMode = "self"
    password_hash = "hashed_password"
    created_at = datetime.now(UTC)

    user = AuthUser(
        user_id=user_id,
        email=email,
        display_name=display_name,
        account_role=account_role,
        profile_mode=profile_mode,
        password_hash=password_hash,
        created_at=created_at,
    )

    assert user.user_id == user_id
    assert user.email == email
    assert user.display_name == display_name
    assert user.account_role == account_role
    assert user.profile_mode == profile_mode
    assert user.password_hash == password_hash
    assert user.created_at == created_at

    # Test default created_at if not provided
    user_no_ts = AuthUser(
        user_id="user_no_ts",
        email="no_ts@example.com",
        display_name="No Timestamp",
        account_role="member",
        profile_mode="self",
        password_hash="hash_no_ts",
    )
    assert user_no_ts.created_at is not None
    assert isinstance(user_no_ts.created_at, datetime)
    assert user_no_ts.created_at.tzinfo == UTC

def test_create_auth_session():
    """
    Tests the creation and attributes of an AuthSession instance.
    """
    session_id = "session_abc"
    user_id = "test_user_123"
    email = "test@example.com"
    account_role: AccountRole = "member"
    profile_mode: ProfileMode = "self"
    scopes = {"read": ["profile"], "write": ["meal"]}
    scopes_json = json.dumps(scopes) # SQLite uses TEXT, so store as string
    display_name = "Test User"
    issued_at = datetime.now(UTC)
    subject_user_id = user_id
    active_household_id = "house_123"

    session = AuthSession(
        session_id=session_id,
        user_id=user_id,
        email=email,
        account_role=account_role,
        profile_mode=profile_mode,
        scopes_json=scopes_json,
        display_name=display_name,
        issued_at=issued_at,
        subject_user_id=subject_user_id,
        active_household_id=active_household_id,
    )

    assert session.session_id == session_id
    assert session.user_id == user_id
    assert session.email == email
    assert session.account_role == account_role
    assert session.profile_mode == profile_mode
    assert session.scopes_json == scopes_json
    assert session.display_name == display_name
    assert session.issued_at == issued_at
    assert session.subject_user_id == subject_user_id
    assert session.active_household_id == active_household_id

    # Test JSON parsing (though not directly tested by instantiation, good to be aware)
    assert json.loads(session.scopes_json) == scopes

def test_auth_user_session_relationship():
    """
    Tests the relationship between AuthUser and AuthSession.
    """
    user = AuthUser(
        user_id="user_rel_test",
        email="rel_test@example.com",
        display_name="Rel User",
        account_role="member",
        profile_mode="self",
        password_hash="hashed_rel_pass",
    )

    session1 = AuthSession(
        session_id="session_rel_1",
        user_id=user.user_id,
        email=user.email,
        account_role=user.account_role,
        profile_mode=user.profile_mode,
        scopes_json='{"read": ["all"]}',
        display_name=user.display_name,
        issued_at=datetime.now(UTC),
    )

    session2 = AuthSession(
        session_id="session_rel_2",
        user_id=user.user_id,
        email=user.email,
        account_role=user.account_role,
        profile_mode=user.profile_mode,
        scopes_json='{"read": ["profile"]}',
        display_name=user.display_name,
        issued_at=datetime.now(UTC) - timedelta(hours=1),
    )

    # Manually associate session with user for test purposes if not using ORM session management
    # In a real ORM session, this would be handled by session.add() and commit.
    # For model testing, we can simulate the relationship.
    user.sessions = [session1, session2]

    assert len(user.sessions) == 2
    assert session1 in user.sessions
    assert session2 in user.sessions
    assert session1.user == user
    assert session2.user == user

def test_create_auth_audit_event():
    """
    Tests the creation and attributes of an AuthAuditEvent instance.
    """
    event_id = "event_audit_1"
    user_id = "user_audit_link" # Assumed user_id
    email = "audit@example.com"
    event_type = "login_success"
    occurred_at = datetime.now(UTC)
    created_at = datetime.now(UTC) - timedelta(minutes=5)
    metadata = {"ip": "192.168.1.1", "user_agent": "test_client"}
    metadata_json = json.dumps(metadata)

    audit_event = AuthAuditEvent(
        event_id=event_id,
        user_id=user_id,
        email=email,
        event_type=event_type,
        occurred_at=occurred_at,
        created_at=created_at,
        metadata_json=metadata_json,
    )

    assert audit_event.event_id == event_id
    assert audit_event.user_id == user_id
    assert audit_event.email == email
    assert audit_event.event_type == event_type
    assert audit_event.occurred_at == occurred_at
    assert audit_event.created_at == created_at
    assert audit_event.metadata_json == metadata_json
    assert json.loads(audit_event.metadata_json) == metadata

    # Test with null user_id
    audit_event_no_user = AuthAuditEvent(
        event_id="event_audit_no_user",
        user_id=None,
        email="no_user@example.com",
        event_type="system_event",
        occurred_at=datetime.now(UTC),
        metadata_json="{}",
    )
    assert audit_event_no_user.user_id is None

def test_create_auth_login_failure():
    """
    Tests the creation and attributes of an AuthLoginFailure instance.
    """
    email = "fail@example.com"
    failed_count = 3
    window_started_at = datetime.now(UTC) - timedelta(minutes=10)
    lockout_until = datetime.now(UTC) + timedelta(hours=1)

    login_failure = AuthLoginFailure(
        email=email,
        failed_count=failed_count,
        window_started_at=window_started_at,
        lockout_until=lockout_until,
    )

    assert login_failure.email == email
    assert login_failure.failed_count == failed_count
    assert login_failure.window_started_at == window_started_at
    assert login_failure.lockout_until == lockout_until

    # Test with None values
    login_failure_no_lock = AuthLoginFailure(
        email="no_lock@example.com",
        failed_count=1,
        window_started_at=datetime.now(UTC),
        lockout_until=None,
    )
    assert login_failure_no_lock.lockout_until is None

# Note: Testing relationships for AuthAuditEvent with AuthUser might require ORM session setup,
# which is beyond simple model instantiation tests. We focus on direct model attributes and structure here.
