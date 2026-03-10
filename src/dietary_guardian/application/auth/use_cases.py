"""Application use cases for auth."""

from dataclasses import dataclass
from typing import Any

from dietary_guardian.domain.identity.models import ProfileMode
from dietary_guardian.infrastructure.auth import AuthUserRecord

from .ports import AuthStorePort


class LoginLockedError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class DuplicateEmailError(Exception):
    pass


class InvalidSignupPasswordError(Exception):
    pass


MIN_PASSWORD_LENGTH = 12


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@dataclass
class AuthSessionResult:
    user: AuthUserRecord
    session: dict[str, Any]


def login_and_create_session(*, auth_store: AuthStorePort, email: str, password: str) -> AuthSessionResult:
    normalized_email = _normalize_email(email)
    if auth_store.is_login_locked(normalized_email):
        auth_store.append_auth_audit_event(
            event_type="login_locked",
            email=normalized_email,
            metadata={"reason": "lockout_active"},
        )
        raise LoginLockedError

    user = auth_store.authenticate(normalized_email, password)
    if user is None:
        now_locked = auth_store.record_login_failure(normalized_email)
        auth_store.append_auth_audit_event(
            event_type="login_failed",
            email=normalized_email,
            metadata={"reason": "invalid_credentials"},
        )
        if now_locked:
            auth_store.append_auth_audit_event(
                event_type="login_locked",
                email=normalized_email,
                metadata={"reason": "too_many_failures"},
            )
        raise InvalidCredentialsError

    auth_store.record_login_success(normalized_email)
    auth_store.append_auth_audit_event(
        event_type="login_success",
        email=normalized_email,
        user_id=user.user_id,
        metadata={"account_role": user.account_role},
    )
    return AuthSessionResult(user=user, session=auth_store.create_session(user))


def signup_member_and_create_session(
    *,
    auth_store: AuthStorePort,
    email: str,
    password: str,
    display_name: str,
    profile_mode: ProfileMode,
) -> AuthSessionResult:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise InvalidSignupPasswordError
    user = auth_store.create_user(
        email=email,
        password=password,
        display_name=display_name,
        account_role="member",
        profile_mode=profile_mode,
    )
    if user is None:
        raise DuplicateEmailError
    auth_store.record_login_success(user.email)
    auth_store.append_auth_audit_event(
        event_type="signup_success",
        email=user.email,
        user_id=user.user_id,
        metadata={"account_role": user.account_role},
    )
    return AuthSessionResult(user=user, session=auth_store.create_session(user))
