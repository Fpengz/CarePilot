"""Profile tool state models for agent and caregiver role contexts.

Provides lightweight Pydantic state containers consumed by the companion
personalization layer to determine which tool capabilities are relevant for
a given session role (self-care, caregiver, clinical export).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SelfToolState(BaseModel):
    recent_meal_names: list[str] = Field(default_factory=list)
    after_meal_reminder_due: bool = False
    meal_confirmation_rate: float | None = None


class CaregiverToolState(BaseModel):
    high_risk_alert_count: int = 0
    manual_review_count: int = 0
    alerts: list[str] = Field(default_factory=list)


class ClinicalSummaryToolState(BaseModel):
    biomarker_summary: dict[str, float] = Field(default_factory=dict)
    narrative: str
    export_payload: dict[str, Any] = Field(default_factory=dict)


__all__ = ["CaregiverToolState", "ClinicalSummaryToolState", "SelfToolState"]
