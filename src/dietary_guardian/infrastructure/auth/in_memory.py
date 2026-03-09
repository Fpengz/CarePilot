import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, cast
from uuid import uuid4

from dietary_guardian.config.settings import Settings
from dietary_guardian.infrastructure.auth.demo_defaults import build_demo_user_seeds
from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.identity import AccountRole, ProfileMode
from dietary_guardian.services.authorization import scopes_for_account_role

logger = get_logger(__name__)


@dataclass
class AuthUserRecord:
    user_id: str
    email: str
    display_name: str
    account_role: AccountRole
    profile_mode: ProfileMode
    password_hash: str


def _pbkdf2_hash(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return "pbkdf2_sha256$200000$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def _pbkdf2_verify(password: str, encoded: str) -> bool:
    try:
        scheme, iterations_s, salt_b64, digest_b64 = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(digest_b64.encode())
    except Exception:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


class PasswordHasher:
    def __init__(self, scheme: str) -> None:
        self.scheme = scheme

    def hash(self, password: str) -> str:
        if self.scheme != "pbkdf2_sha256":
            raise ValueError(f"Unsupported hash scheme: {self.scheme}")
        return _pbkdf2_hash(password)

    def verify(self, password: str, encoded: str) -> bool:
        if encoded.startswith("pbkdf2_sha256$"):
            return _pbkdf2_verify(password, encoded)
        return False


class InMemoryAuthStore:
    def __init__(self, settings: Settings) -> None:
        self._hasher = PasswordHasher(settings.auth.password_hash_scheme)
        self._demo_defaults = build_demo_user_seeds(settings)
        self._session_ttl_seconds = int(settings.auth.session_ttl_seconds)
        self._login_max_failed_attempts = int(settings.auth.login_max_failed_attempts)
        self._login_failure_window_seconds = int(settings.auth.login_failure_window_seconds)
        self._login_lockout_seconds = int(settings.auth.login_lockout_seconds)
        self._auth_audit_events_max_entries = int(settings.auth.audit_events_max_entries)
        self._users_by_email: dict[str, AuthUserRecord] = {}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._login_failures: dict[str, dict[str, Any]] = {}
        self._auth_audit_events: list[dict[str, Any]] = []
        if settings.auth.seed_demo_users:
            self._seed_defaults()

    def _seed_defaults(self) -> None:
        for user_id, email, name, account_role, profile_mode, password in self._demo_defaults:
            self._users_by_email[email] = AuthUserRecord(
                user_id=user_id,
                email=email,
                display_name=name,
                account_role=account_role,  # type: ignore[arg-type]
                profile_mode=profile_mode,  # type: ignore[arg-type]
                password_hash=self._hasher.hash(password),
            )

    def authenticate(self, email: str, password: str) -> AuthUserRecord | None:
        user = self._users_by_email.get(email)
        if user is None:
            return None
        if not self._hasher.verify(password, user.password_hash):
            return None
        return user

    def create_user(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        account_role: AccountRole = "member",
        profile_mode: ProfileMode = "self",
    ) -> AuthUserRecord | None:
        normalized_email = email.strip().lower()
        if not normalized_email or normalized_email in self._users_by_email:
            return None
        user = AuthUserRecord(
            user_id=f"user_{uuid4().hex[:12]}",
            email=normalized_email,
            display_name=display_name,
            account_role=account_role,
            profile_mode=profile_mode,
            password_hash=self._hasher.hash(password),
        )
        self._users_by_email[normalized_email] = user
        return user

    def is_login_locked(self, email: str) -> bool:
        state = self._login_failures.get(email)
        if not state:
            return False
        lockout_until_raw = state.get("lockout_until")
        if not isinstance(lockout_until_raw, str):
            return False
        try:
            lockout_until = datetime.fromisoformat(lockout_until_raw)
        except ValueError:
            self._login_failures.pop(email, None)
            return False
        if lockout_until.tzinfo is None:
            lockout_until = lockout_until.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= lockout_until.astimezone(timezone.utc):
            state["lockout_until"] = None
            state["failed_count"] = 0
            state["window_started_at"] = None
            return False
        return True

    def record_login_failure(self, email: str) -> bool:
        now = datetime.now(timezone.utc)
        state = self._login_failures.get(email)
        if state is None:
            state = {"failed_count": 0, "window_started_at": None, "lockout_until": None}
            self._login_failures[email] = state
        window_started_raw = state.get("window_started_at")
        reset_window = True
        if isinstance(window_started_raw, str):
            try:
                window_started = datetime.fromisoformat(window_started_raw)
                if window_started.tzinfo is None:
                    window_started = window_started.replace(tzinfo=timezone.utc)
                reset_window = (
                    now - window_started.astimezone(timezone.utc)
                ).total_seconds() > self._login_failure_window_seconds
            except ValueError:
                reset_window = True
        if reset_window:
            state["failed_count"] = 0
            state["window_started_at"] = now.isoformat()
        current_failed_count_raw = state.get("failed_count", 0)
        current_failed_count = current_failed_count_raw if isinstance(current_failed_count_raw, int) else 0
        state["failed_count"] = current_failed_count + 1
        state["lockout_until"] = None
        failed_count = cast(int, state["failed_count"])
        if failed_count >= self._login_max_failed_attempts:
            state["lockout_until"] = (now + timedelta(seconds=self._login_lockout_seconds)).isoformat()
            return True
        return False

    def record_login_success(self, email: str) -> None:
        self._login_failures.pop(email, None)

    def append_auth_audit_event(
        self,
        *,
        event_type: str,
        email: str,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = {
            "event_id": str(uuid4()),
            "event_type": event_type,
            "email": email,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": dict(metadata or {}),
        }
        self._auth_audit_events.insert(0, event)
        if len(self._auth_audit_events) > self._auth_audit_events_max_entries:
            del self._auth_audit_events[self._auth_audit_events_max_entries :]

    def list_auth_audit_events(self, *, limit: int = 50) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), 200))
        return [dict(item) for item in self._auth_audit_events[:bounded]]

    def update_user_profile(
        self,
        *,
        user_id: str,
        display_name: str | None = None,
        profile_mode: ProfileMode | None = None,
    ) -> AuthUserRecord | None:
        user: AuthUserRecord | None = None
        for candidate in self._users_by_email.values():
            if candidate.user_id == user_id:
                user = candidate
                break
        if user is None:
            return None
        if display_name is not None:
            user.display_name = display_name
        if profile_mode is not None:
            user.profile_mode = profile_mode
        for session in self._sessions.values():
            if str(session.get("user_id")) != user_id:
                continue
            if display_name is not None:
                session["display_name"] = display_name
            if profile_mode is not None:
                session["profile_mode"] = profile_mode
        return user

    def change_user_password(
        self,
        *,
        user_id: str,
        current_password: str,
        new_password: str,
        keep_session_id: str,
    ) -> tuple[bool, int]:
        user: AuthUserRecord | None = None
        for candidate in self._users_by_email.values():
            if candidate.user_id == user_id:
                user = candidate
                break
        if user is None:
            return (False, 0)
        if not self._hasher.verify(current_password, user.password_hash):
            return (False, 0)
        user.password_hash = self._hasher.hash(new_password)
        revoked_count = self.revoke_other_sessions(user_id, keep_session_id=keep_session_id)
        return (True, revoked_count)

    def create_session(self, user: AuthUserRecord) -> dict[str, Any]:
        session_id = str(uuid4())
        session = {
            "session_id": session_id,
            "user_id": user.user_id,
            "email": user.email,
            "account_role": user.account_role,
            "profile_mode": user.profile_mode,
            "scopes": scopes_for_account_role(user.account_role),
            "display_name": user.display_name,
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "subject_user_id": user.user_id,
            "active_household_id": None,
        }
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        issued_at_raw = session.get("issued_at")
        if not isinstance(issued_at_raw, str):
            self.destroy_session(session_id)
            return None
        try:
            issued_at = datetime.fromisoformat(issued_at_raw)
        except ValueError:
            self.destroy_session(session_id)
            return None
        if issued_at.tzinfo is None:
            issued_at = issued_at.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - issued_at.astimezone(timezone.utc)).total_seconds()
        if age_seconds > self._session_ttl_seconds:
            self.destroy_session(session_id)
            return None
        return session

    def destroy_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def list_sessions_for_user(self, user_id: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for session_id, _session in list(self._sessions.items()):
            resolved = self.get_session(session_id)
            if resolved is None:
                continue
            if str(resolved.get("user_id")) != user_id:
                continue
            items.append(resolved)
        items.sort(key=lambda item: str(item.get("issued_at", "")), reverse=True)
        return items

    def get_session_owner(self, session_id: str) -> str | None:
        session = self.get_session(session_id)
        if session is None:
            return None
        user_id = session.get("user_id")
        return str(user_id) if isinstance(user_id, str) else None

    def revoke_other_sessions(self, user_id: str, *, keep_session_id: str) -> int:
        revoked = 0
        for session in self.list_sessions_for_user(user_id):
            session_id = str(session.get("session_id", ""))
            if not session_id or session_id == keep_session_id:
                continue
            self.destroy_session(session_id)
            revoked += 1
        return revoked

    def set_active_household_for_session(
        self, session_id: str, *, active_household_id: str | None
    ) -> dict[str, Any] | None:
        session = self.get_session(session_id)
        if session is None:
            return None
        session["active_household_id"] = active_household_id
        return session

    def close(self) -> None:
        return None
