"""
Define auth port protocols.

This module contains protocol interfaces for authentication persistence
and session management.
"""

from typing import Any, Protocol

from care_pilot.features.profiles.domain.models import AccountRole, ProfileMode
from care_pilot.platform.auth.in_memory import AuthUserRecord


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
    def get_session(self, session_id: str) -> dict[str, Any] | None: ...
    def destroy_session(self, session_id: str) -> None: ...
    def create_user(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        account_role: AccountRole = "member",
        profile_mode: ProfileMode = "self",
    ) -> AuthUserRecord | None: ...
    def update_user_profile(
        self,
        user_id: str,
        *,
        display_name: str | None = None,
        profile_mode: ProfileMode | None = None,
    ) -> AuthUserRecord | None: ...
    def change_user_password(
        self,
        *,
        user_id: str,
        current_password: str,
        new_password: str,
        keep_session_id: str,
    ) -> tuple[bool, int]: ...
    def list_sessions_for_user(self, user_id: str) -> list[dict[str, Any]]: ...
    def revoke_other_sessions(self, user_id: str, *, keep_session_id: str) -> int: ...
    def get_session_owner(self, session_id: str) -> str | None: ...
    def list_auth_audit_events(self, *, limit: int = 50) -> list[dict[str, Any]]: ...
    def set_active_household_for_session(
        self, session_id: str, *, active_household_id: str | None
    ) -> dict[str, Any] | None: ...
    def close(self) -> None: ...
