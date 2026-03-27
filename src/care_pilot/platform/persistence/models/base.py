"""
Base classes and mixins for SQLModel persistence.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func
from sqlmodel import Field, SQLModel


class TimestampMixin(SQLModel):
    """Mixin to add created_at and updated_at timestamps to a model."""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={
            "server_default": func.now(),
            "onupdate": func.now(),
        },
    )


class BaseRecord(SQLModel):
    """Base class for all persistent records with a unique ID."""

    pass
