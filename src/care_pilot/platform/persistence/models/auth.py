"""
Auth and Account persistence models.
"""

from __future__ import annotations

from sqlmodel import Field

from care_pilot.platform.persistence.models.base import BaseRecord, TimestampMixin


class AccountRecord(BaseRecord, TimestampMixin, table=True):
    """
    SQLModel implementation of a system account.
    This replaces the in-memory and raw SQL auth records.
    """

    __tablename__ = "accounts"

    id: str = Field(primary_key=True)
    email: str = Field(index=True, unique=True, nullable=False)
    password_hash: str = Field(nullable=False)
    display_name: str = Field(nullable=False)
    role: str = Field(default="member")
    profile_mode: str = Field(default="self")

    # The subject_user_id links the auth account to the clinical profile.
    # Usually 1:1, but designed for 1:N caregiver support in the future.
    subject_user_id: str | None = Field(default=None, index=True, foreign_key="user_profiles.id")
