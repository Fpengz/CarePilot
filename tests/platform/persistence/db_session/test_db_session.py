"""
Tests for the AuthSQLModelSessionManager.
"""

from unittest.mock import MagicMock

import pytest
from sqlmodel import Session, create_engine

from care_pilot.platform.persistence.db_session import AuthSQLModelSessionManager


def test_auth_sqlmodel_session_manager_init():
    """Tests the initialization of the AuthSQLModelSessionManager."""
    engine = create_engine("sqlite:///:memory:")
    session_manager = AuthSQLModelSessionManager(engine=engine)
    assert session_manager.engine == engine

def test_auth_sqlmodel_session_manager_yields_session():
    """Tests that get_session yields a SQLModel Session and closes it."""
    engine = create_engine("sqlite:///:memory:")
    session_manager = AuthSQLModelSessionManager(engine=engine)

    # Consume the context manager to exercise commit/close behavior.
    try:
        with session_manager.get_session() as session:
            assert isinstance(session, Session)
    except Exception as exc:
        pytest.fail(f"Unexpected exception during yield test: {exc}")


def test_auth_sqlmodel_session_manager_commits_on_success(monkeypatch):
    """Tests that session.commit() is called on successful yield."""
    engine = create_engine("sqlite:///:memory:")
    session_manager = AuthSQLModelSessionManager(engine=engine)

    # Mock the Session instance itself, and its methods
    mock_session_instance = MagicMock(spec=Session)
    mock_session_instance.commit = MagicMock()
    mock_session_instance.rollback = MagicMock()
    mock_session_instance.close = MagicMock()

    # Patch the Session constructor to return our mock instance
    monkeypatch.setattr(
        "care_pilot.platform.persistence.db_session.Session",
        lambda *_args, **_kwargs: mock_session_instance,
    )
    try:
        with session_manager.get_session() as session:
            session.add(object())
    except Exception as exc:
        pytest.fail(f"Unexpected exception during commit test: {exc}")

    mock_session_instance.commit.assert_called_once()
    mock_session_instance.rollback.assert_not_called()
    mock_session_instance.close.assert_called_once() # Ensure close is also called

def test_auth_sqlmodel_session_manager_rollbacks_on_exception(monkeypatch):
    """Tests that session.rollback() is called on exception."""
    engine = create_engine("sqlite:///:memory:")
    session_manager = AuthSQLModelSessionManager(engine=engine)

    # Mock session.commit and session.rollback
    mock_session_instance = MagicMock(spec=Session)
    mock_session_instance.commit = MagicMock()
    mock_session_instance.rollback = MagicMock()
    mock_session_instance.close = MagicMock() # Mock close as well

    # Patch the Session constructor to return our mock instance
    monkeypatch.setattr(
        "care_pilot.platform.persistence.db_session.Session",
        lambda *_args, **_kwargs: mock_session_instance,
    )
    with pytest.raises(ValueError, match="Simulated error"), session_manager.get_session():
        raise ValueError("Simulated error")

    mock_session_instance.commit.assert_not_called()
    mock_session_instance.rollback.assert_called_once()
    mock_session_instance.close.assert_called_once() # Ensure close is also called

# Note: Testing relationships directly on models when just instantiating is complex.
# These tests focus on the session management logic itself.
# Relationship tests would ideally be integration tests involving a database.
