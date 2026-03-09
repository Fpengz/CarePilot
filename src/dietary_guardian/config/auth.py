"""Authentication and session storage settings for runtime identity flows."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, populate_by_name=True)

    session_secret: str = Field(default="dev-insecure-session-secret-change-me", validation_alias="SESSION_SECRET")
    cookie_secure: bool = Field(default=False, validation_alias="COOKIE_SECURE")
    cookie_samesite: Literal["lax", "strict", "none"] = Field(default="lax", validation_alias="COOKIE_SAMESITE")
    password_hash_scheme: str = Field(default="pbkdf2_sha256", validation_alias="AUTH_PASSWORD_HASH_SCHEME")
    store_backend: Literal["in_memory", "sqlite"] = Field(default="sqlite", validation_alias="AUTH_STORE_BACKEND")
    sqlite_db_path: str = Field(default="dietary_guardian_auth.db", validation_alias="AUTH_SQLITE_DB_PATH")
    session_ttl_seconds: int = Field(default=86400, ge=1, le=60 * 60 * 24 * 30, validation_alias="AUTH_SESSION_TTL_SECONDS")
    login_max_failed_attempts: int = Field(default=5, ge=1, le=20, validation_alias="AUTH_LOGIN_MAX_FAILED_ATTEMPTS")
    login_failure_window_seconds: int = Field(default=300, ge=1, le=3600, validation_alias="AUTH_LOGIN_FAILURE_WINDOW_SECONDS")
    login_lockout_seconds: int = Field(default=300, ge=1, le=86400, validation_alias="AUTH_LOGIN_LOCKOUT_SECONDS")
    audit_events_max_entries: int = Field(default=500, ge=10, le=10000, validation_alias="AUTH_AUDIT_EVENTS_MAX_ENTRIES")
    seed_demo_users: bool | None = Field(default=None, validation_alias="AUTH_SEED_DEMO_USERS")
    demo_member_password: str = Field(default="member-pass", validation_alias="AUTH_DEMO_MEMBER_PASSWORD")
    demo_helper_password: str = Field(default="helper-pass", validation_alias="AUTH_DEMO_HELPER_PASSWORD")
    demo_admin_password: str = Field(default="admin-pass", validation_alias="AUTH_DEMO_ADMIN_PASSWORD")
