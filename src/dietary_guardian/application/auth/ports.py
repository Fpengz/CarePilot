from typing import Any, Protocol

from dietary_guardian.infrastructure.auth import AuthUserRecord
from dietary_guardian.models.identity import AccountRole, ProfileMode


class AuthStorePort(Protocol):
    def is_login_locked(self, email: str) -> bool: ...
    def authenticate(self, email: str, password: str) -> AuthUserRecord | None: ...
    def record_login_failure(self, email: str) -> bool: ...
    def record_login_success(self, email: str) -> None: ...
    def append_auth_audit_event(
        self,
        *,
        event_type: str,
        email: str,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...
    def create_session(self, user: AuthUserRecord) -> dict[str, Any]: ...
    def create_user(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        account_role: AccountRole = "member",
        profile_mode: ProfileMode = "self",
    ) -> AuthUserRecord | None: ...
