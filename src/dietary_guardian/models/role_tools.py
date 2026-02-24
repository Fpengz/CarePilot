from typing import Any

from pydantic import BaseModel, Field


class PatientToolState(BaseModel):
    recent_meal_names: list[str] = Field(default_factory=list)
    after_meal_reminder_due: bool = False
    meal_confirmation_rate: float | None = None


class CaregiverToolState(BaseModel):
    high_risk_alert_count: int = 0
    manual_review_count: int = 0
    alerts: list[str] = Field(default_factory=list)


class ClinicianToolState(BaseModel):
    biomarker_summary: dict[str, float] = Field(default_factory=dict)
    narrative: str
    export_payload: dict[str, Any] = Field(default_factory=dict)
