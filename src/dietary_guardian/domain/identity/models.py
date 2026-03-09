"""Domain model definitions for the identity subdomain: accounts, users, and meal scheduling."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AccountRole = Literal["member", "admin"]
ProfileMode = Literal["self", "caregiver"]
PermissionScope = Literal[
    "meal:write",
    "meal:read",
    "report:write",
    "report:read",
    "recommendation:generate",
    "reminder:write",
    "reminder:read",
    "alert:trigger",
    "alert:timeline:read",
    "workflow:read",
    "workflow:replay",
    "workflow:write",
    "auth:audit:read",
]

MealSlot = Literal["breakfast", "lunch", "dinner", "snack"]


class AccountPrincipal(BaseModel):
    account_id: str
    email: str
    display_name: str
    account_role: AccountRole
    scopes: list[str] = Field(default_factory=list)
    profile_mode: ProfileMode = "self"
    subject_user_id: str | None = None


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
    contraindications: set[str] = Field(default_factory=set)


class UserProfile(BaseModel):
    id: str
    name: str
    age: int
    conditions: list[MedicalCondition]
    medications: list[Medication]
    profile_mode: ProfileMode = "self"
    locale: str = "en-SG"
    allergies: list[str] = Field(default_factory=list)
    nutrition_goals: list[str] = Field(default_factory=list)
    preferred_cuisines: list[str] = Field(default_factory=list)
    disliked_ingredients: list[str] = Field(default_factory=list)
    budget_tier: Literal["budget", "moderate", "flexible"] = "moderate"
    target_calories_per_day: float | None = None
    macro_focus: list[str] = Field(default_factory=list)
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
    daily_protein_target_g: float = 60.0
    daily_fiber_target_g: float = 25.0
