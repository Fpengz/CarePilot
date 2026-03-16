"""
Define clinical card domain models.

This module contains the data models used to represent clinician cards.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field

ClinicalCardFormat = Literal["sectioned", "soap"]


class ClinicalCardRecord(BaseModel):
    id: str
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    start_date: date
    end_date: date
    format: ClinicalCardFormat = "sectioned"
    sections: dict[str, str] = Field(default_factory=dict)
    deltas: dict[str, float] = Field(default_factory=dict)
    trends: dict[str, dict[str, object]] = Field(default_factory=dict)
    provenance: dict[str, object] = Field(default_factory=dict)
