"""Tests for session signer."""

import time

from dietary_guardian.infrastructure.auth.session_signer import SessionSigner


def test_session_signer_unsign_valid_token_within_max_age() -> None:
    signer = SessionSigner("test-secret")
    token = signer.sign("session-123")
    assert signer.unsign(token, max_age_seconds=10) == "session-123"


def test_session_signer_rejects_expired_token() -> None:
    signer = SessionSigner("test-secret")
    token = signer.sign("session-123")
    time.sleep(2.1)
    assert signer.unsign(token, max_age_seconds=1) is None
