from typing import Literal

from pydantic import BaseModel, Field

AccountRole = Literal["member", "admin"]
ProfileMode = Literal["self", "caregiver"]
PermissionScope = Literal[
    "meal:write",
    "meal:read",
    "report:write",
    "report:read",
    "recommendation:generate",
    "reminder:write",
    "reminder:read",
    "alert:trigger",
    "alert:timeline:read",
    "workflow:read",
    "workflow:replay",
    "workflow:write",
    "auth:audit:read",
]


class AccountPrincipal(BaseModel):
    account_id: str
    email: str
    display_name: str
    account_role: AccountRole
    scopes: list[str] = Field(default_factory=list)
    profile_mode: ProfileMode = "self"
    subject_user_id: str | None = None
