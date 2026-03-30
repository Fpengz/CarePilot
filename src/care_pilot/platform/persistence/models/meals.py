"""
MealRecord persistence models.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Column
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship  # Import Relationship

from care_pilot.platform.persistence.models.base import BaseRecord, TimestampMixin
from care_pilot.platform.persistence.models.meal_components import (
    MealComponentRecord,  # Import new model
)

if TYPE_CHECKING:
    from care_pilot.platform.persistence.models.profiles import UserProfileRecord


class MealRecordRecord(BaseRecord, TimestampMixin, table=True):
    """
    SQLModel implementation of a meal record.
    Supports multi-modal data (images, embedding) and agent perceptions.
    """

    __tablename__ = "meal_records"

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True, foreign_key="user_profiles.id")
    captured_at: datetime = Field(index=True)
    source: str  # e.g., "camera", "chat", "audio"

    # Removed JSON fields: meal_state, meal_perception
    # enriched_event remains as JSON for now, as its structure is less defined for normalization.
    enriched_event: dict | None = Field(default=None, sa_column=Column(JSON))

    # Multi-modality & Search
    media_url: str | None = None  # Pointer to Cloud Storage
    embedding_v1: list[float] | None = Field(
        default=None, sa_column=Column(JSON)
    )  # For semantic search over meals

    analysis_version: str
    multi_item_count: int = 0

    # Define ORM relationships
    user_profile: Mapped["UserProfileRecord"] = Relationship(back_populates="meal_records")
    meal_components: Mapped[list["MealComponentRecord"]] = Relationship(
        back_populates="meal_record"
    )
