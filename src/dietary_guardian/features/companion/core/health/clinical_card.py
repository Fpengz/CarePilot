"""Data models for clinical card."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

ClinicalCardFormat = Literal["sectioned", "soap"]


class ClinicalCardRecord(BaseModel):
    id: str
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    start_date: date
    end_date: date
    format: ClinicalCardFormat = "sectioned"
    sections: dict[str, str] = Field(default_factory=dict)
    deltas: dict[str, float] = Field(default_factory=dict)
    trends: dict[str, dict[str, object]] = Field(default_factory=dict)
    provenance: dict[str, object] = Field(default_factory=dict)
