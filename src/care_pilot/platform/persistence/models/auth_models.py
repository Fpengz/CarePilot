"""
Define SQLModel classes for auth entities.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, Column
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

# Keep SQLModel-compatible annotations for persistence.
AccountRole = str
ProfileMode = str


class AuthUser(SQLModel, table=True):
    __tablename__ = "auth_users"

    user_id: str = Field(primary_key=True)
    email: str = Field(unique=True, index=True)
    display_name: str
    account_role: AccountRole
    profile_mode: ProfileMode
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Define relationship to AuthSession
    sessions: Mapped[list["AuthSession"]] = Relationship(back_populates="user")
    # Define relationship to AuthAuditEvent
    audit_events: Mapped[list["AuthAuditEvent"]] = Relationship(back_populates="user")


class AuthSession(SQLModel, table=True):
    __tablename__ = "auth_sessions"

    session_id: str = Field(primary_key=True)
    user_id: str = Field(index=True, foreign_key="auth_users.user_id")  # FK to AuthUser
    email: str
    account_role: AccountRole
    profile_mode: ProfileMode
    scopes_json: str  # Store as JSON string
    display_name: str
    issued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    subject_user_id: str | None = None  # Can be same as user_id or related user
    active_household_id: str | None = None

    # Define relationship to AuthUser
    user: Mapped[AuthUser] = Relationship(back_populates="sessions")


class AuthAuditEvent(SQLModel, table=True):
    __tablename__ = "auth_audit_events"

    event_id: str = Field(primary_key=True)
    user_id: str | None = Field(
        default=None, index=True, foreign_key="auth_users.user_id"
    )  # FK to AuthUser
    email: str  # Store email for context even if user_id is null
    event_type: str
    occurred_at: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata_json: str = Field(default="{}", sa_column=Column(JSON))  # Use JSON type for metadata

    # Define relationship to AuthUser (optional, could be nullable)
    user: Mapped[AuthUser | None] = Relationship(back_populates="audit_events")


class AuthLoginFailure(SQLModel, table=True):
    __tablename__ = "auth_login_failures"

    email: str = Field(primary_key=True)
    failed_count: int = Field(default=0)
    window_started_at: datetime | None = None
    lockout_until: datetime | None = None
