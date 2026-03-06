from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


AdherenceStatus = Literal["taken", "missed", "skipped", "unknown"]
AdherenceSource = Literal["manual", "reminder_confirm", "imported"]


class MedicationAdherenceEvent(BaseModel):
    id: str
    user_id: str
    regimen_id: str
    reminder_id: str | None = None
    status: AdherenceStatus
    scheduled_at: datetime
    taken_at: datetime | None = None
    source: AdherenceSource = "manual"
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MedicationAdherenceMetrics(BaseModel):
    events: int = 0
    taken: int = 0
    missed: int = 0
    skipped: int = 0
    adherence_rate: float = 0.0
