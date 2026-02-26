import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, cast
from uuid import uuid4

from itsdangerous import BadSignature, URLSafeSerializer

from dietary_guardian.config.settings import Settings
from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.identity import AccountRole, ProfileMode
from dietary_guardian.models.user import MedicalCondition, Medication, UserProfile
from dietary_guardian.services.authorization import default_profile_mode_for_role, scopes_for_account_role

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
        self._hasher = PasswordHasher(settings.auth_password_hash_scheme)
        self._session_ttl_seconds = int(settings.auth_session_ttl_seconds)
        self._users_by_email: dict[str, AuthUserRecord] = {}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        defaults = [
            ("user_001", "member@example.com", "Alex Member", "member", "self", "member-pass"),
            ("care_001", "helper@example.com", "Casey Helper", "member", "caregiver", "helper-pass"),
            ("ops_001", "admin@example.com", "Ops Admin", "admin", "self", "admin-pass"),
        ]
        for user_id, email, name, account_role, profile_mode, password in defaults:
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


class SessionSigner:
    def __init__(self, secret: str) -> None:
        self._serializer = URLSafeSerializer(secret, salt="dietary-guardian-session")

    def sign(self, session_id: str) -> str:
        return self._serializer.dumps({"sid": session_id})

    def unsign(self, token: str) -> str | None:
        try:
            data = self._serializer.loads(token)
        except BadSignature:
            return None
        return str(data.get("sid")) if isinstance(data, dict) else None


def build_user_profile_from_session(session: dict[str, Any]) -> UserProfile:
    # Minimal profile for coordinator/authz contexts; domain-rich data can be loaded later.
    return UserProfile(
        id=str(session["user_id"]),
        name=str(session["display_name"]),
        age=68,
        conditions=[MedicalCondition(name="Diabetes", severity="High")],
        medications=[Medication(name="Warfarin", dosage="5mg")],
        profile_mode=cast(
            ProfileMode,
            session.get("profile_mode")
            or default_profile_mode_for_role(cast(AccountRole, session["account_role"])),
        ),
    )
