from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class SymptomSafety(BaseModel):
    decision: str = "allow"
    reasons: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    redactions: list[str] = Field(default_factory=list)


class SymptomCheckIn(BaseModel):
    id: str
    user_id: str
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    severity: int = Field(ge=1, le=5)
    symptom_codes: list[str] = Field(default_factory=list)
    free_text: str | None = None
    context: dict[str, object] = Field(default_factory=dict)
    safety: SymptomSafety = Field(default_factory=SymptomSafety)


class SymptomCount(BaseModel):
    code: str
    count: int


class SymptomSummary(BaseModel):
    total_count: int = 0
    average_severity: float = 0.0
    red_flag_count: int = 0
    top_symptoms: list[SymptomCount] = Field(default_factory=list)
    latest_recorded_at: datetime | None = None
