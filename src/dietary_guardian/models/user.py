from typing import List, Literal, Set

from pydantic import BaseModel, Field

UserRole = Literal["patient", "caregiver", "clinician"]
MealSlot = Literal["breakfast", "lunch", "dinner", "snack"]


class MealScheduleWindow(BaseModel):
    slot: MealSlot
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    timezone: str = "Asia/Singapore"


class MedicalCondition(BaseModel):
    name: str
    severity: str  # "Low", "Medium", "High", "Critical"


class Medication(BaseModel):
    name: str
    dosage: str
    contraindications: Set[str] = Field(
        default_factory=set
    )  # e.g., {"Tyramine", "High Sodium"}


class UserProfile(BaseModel):
    id: str
    name: str
    age: int
    conditions: List[MedicalCondition]
    medications: List[Medication]
    role: UserRole = "patient"
    meal_schedule: list[MealScheduleWindow] = Field(
        default_factory=lambda: [
            MealScheduleWindow(slot="breakfast", start_time="07:00", end_time="09:00"),
            MealScheduleWindow(slot="lunch", start_time="12:00", end_time="14:00"),
            MealScheduleWindow(slot="dinner", start_time="18:00", end_time="20:00"),
        ]
    )
    preferred_notification_channel: str = "in_app"
    daily_sodium_limit_mg: float = 2000.0
    daily_sugar_limit_g: float = 30.0
