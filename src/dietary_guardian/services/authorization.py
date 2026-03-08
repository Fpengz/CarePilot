from dietary_guardian.models.identity import AccountRole, ProfileMode

MEMBER_SCOPES: set[str] = {
    "meal:write",
    "meal:read",
    "report:write",
    "report:read",
    "recommendation:generate",
    "reminder:write",
    "reminder:read",
    "emotion:infer",
}
ADMIN_EXTRA_SCOPES: set[str] = {
    "alert:trigger",
    "alert:timeline:read",
    "workflow:read",
    "workflow:replay",
    "workflow:write",
    "auth:audit:read",
}


def scopes_for_account_role(account_role: AccountRole) -> list[str]:
    scopes = set(MEMBER_SCOPES)
    if account_role == "admin":
        scopes |= ADMIN_EXTRA_SCOPES
    return sorted(scopes)


def has_scopes(current_scopes: list[str], required_scopes: set[str]) -> bool:
    return required_scopes.issubset(set(current_scopes))


def default_profile_mode_for_role(account_role: AccountRole) -> ProfileMode:
    return "self"
