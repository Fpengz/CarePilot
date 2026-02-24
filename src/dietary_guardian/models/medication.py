from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from dietary_guardian.models.user import MealSlot

TimingType = Literal["pre_meal", "post_meal", "fixed_time"]
ReminderStatus = Literal["sent", "acknowledged", "missed"]
MealConfirmation = Literal["yes", "no", "unknown"]


class MedicationRegimen(BaseModel):
    id: str
    user_id: str
    medication_name: str
    dosage_text: str
    timing_type: TimingType
    offset_minutes: int = 0
    slot_scope: list[MealSlot] = Field(default_factory=list)
    fixed_time: str | None = None  # HH:MM, only for fixed_time
    max_daily_doses: int = 1
    active: bool = True


class ReminderEvent(BaseModel):
    id: str
    user_id: str
    medication_name: str
    scheduled_at: datetime
    slot: MealSlot | None = None
    dosage_text: str
    status: ReminderStatus = "sent"
    meal_confirmation: MealConfirmation = "unknown"
    sent_at: datetime | None = None
    ack_at: datetime | None = None
