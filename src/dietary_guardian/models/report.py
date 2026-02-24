from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class ReportInput(BaseModel):
    source: Literal["pdf", "pasted_text"]
    content_bytes: bytes | None = None
    text: str | None = None
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BiomarkerReading(BaseModel):
    name: str
    value: float
    unit: str | None = None
    reference_range: str | None = None
    measured_at: datetime | None = None
    source_doc_id: str | None = None


class ClinicalProfileSnapshot(BaseModel):
    biomarkers: dict[str, float] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)
