"""Typed contracts for medication intake parsing and normalization."""

from __future__ import annotations

from datetime import date
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from dietary_guardian.features.profiles.domain.models import MealSlot


MedicationIntakeSourceType = Literal["plain_text", "upload"]
MedicationFrequencyType = Literal["times_per_day", "fixed_slots", "fixed_time"]
MedicationTimingType = Literal["pre_meal", "post_meal", "fixed_time"]


class MedicationIntakeSource(BaseModel):
    source_type: MedicationIntakeSourceType
    extracted_text: str
    filename: str | None = None
    mime_type: str | None = None
    source_hash: str


class NormalizedMedicationInstruction(BaseModel):
    medication_name_raw: str
    medication_name_canonical: str | None = None
    dosage_text: str
    timing_type: MedicationTimingType
    frequency_type: MedicationFrequencyType = "fixed_time"
    frequency_times_per_day: int = 1
    offset_minutes: int = 0
    slot_scope: list[MealSlot] = Field(default_factory=list)
    fixed_time: str | None = None
    time_rules: list[dict[str, object]] = Field(default_factory=list)
    duration_days: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    confidence: float = 0.0
    ambiguities: list[str] = Field(default_factory=list)


class LLMNormalizedMedicationInstruction(BaseModel):
    medication_name_raw: str
    medication_name_canonical: str | None = None
    dosage_text: str
    timing_type: str | None = None
    frequency_type: str | None = None
    frequency_times_per_day: int | None = None
    offset_minutes: int | None = None
    slot_scope: list[MealSlot] | None = None
    fixed_time: str | None = None
    time_rules: list[dict[str, object]] | None = None
    duration_days: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    confidence: float | None = None
    ambiguities: list[str] | None = None


class MedicationIntakeParseResult(BaseModel):
    source: MedicationIntakeSource
    instructions: list[NormalizedMedicationInstruction] = Field(default_factory=list)


class MedicationIntakeDraft(BaseModel):
    draft_id: str
    user_id: str
    timezone_name: str
    source: MedicationIntakeSource
    instructions: list[NormalizedMedicationInstruction] = Field(default_factory=list)


class MedicationParseOutput(BaseModel):
    instructions: list[NormalizedMedicationInstruction] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class MedicationParseOutputLoose(BaseModel):
    instructions: list[LLMNormalizedMedicationInstruction] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class MedicationInferenceEngineProtocol(Protocol):
    async def infer(self, request: object) -> object: ...
