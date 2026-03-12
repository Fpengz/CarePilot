"""
Define household feature ports.

This module declares interfaces used by household application workflows.
"""

from typing import Any, Protocol

from dietary_guardian.config.app import AppSettings as Settings
from dietary_guardian.platform.observability.workflows.coordinator import WorkflowCoordinator
from dietary_guardian.platform.persistence import AppStores


class HouseholdStorePort(Protocol):
    def get_household_for_user(self, user_id: str) -> dict[str, Any] | None: ...
    def get_household_by_id(self, household_id: str) -> dict[str, Any] | None: ...
    def create_household(self, *, owner_user_id: str, owner_display_name: str, name: str) -> dict[str, Any]: ...
    def list_members(self, household_id: str) -> list[dict[str, Any]]: ...
    def get_member_role(self, household_id: str, user_id: str) -> str | None: ...
    def rename_household(self, *, household_id: str, name: str) -> dict[str, Any] | None: ...
    def create_invite(self, *, household_id: str, created_by_user_id: str) -> dict[str, Any]: ...
    def join_by_invite(
        self, *, code: str, user_id: str, display_name: str
    ) -> tuple[dict[str, Any], bool] | None: ...
    def remove_member(self, *, household_id: str, user_id: str) -> bool: ...


class AuthStorePort(Protocol):
    def set_active_household_for_session(
        self, session_id: str, *, active_household_id: str | None
    ) -> Any: ...


class HouseholdContext(Protocol):
    """Structural protocol for AppContext used by household use cases."""

    @property
    def settings(self) -> Settings: ...

    @property
    def stores(self) -> AppStores: ...

    @property
    def coordinator(self) -> WorkflowCoordinator: ...

    @property
    def household_store(self) -> HouseholdStorePort: ...

    @property
    def auth_store(self) -> AuthStorePort: ...
