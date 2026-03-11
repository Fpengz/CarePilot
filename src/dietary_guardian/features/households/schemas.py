"""Household feature Pydantic schemas shared between domain and API layers."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from dietary_guardian.features.companion.core.health.analytics import EngagementMetrics
from dietary_guardian.features.meals.schemas import MealDailySummaryResponse
from dietary_guardian.features.profiles.schemas import HealthProfileResponseItem
from dietary_guardian.features.reminders.domain.models import ReminderEvent


class HouseholdCreateRequest(BaseModel):
    name: str


class HouseholdUpdateRequest(BaseModel):
    name: str


class HouseholdResponse(BaseModel):
    household_id: str
    name: str
    owner_user_id: str
    created_at: datetime


class HouseholdMemberItem(BaseModel):
    user_id: str
    display_name: str
    role: Literal["owner", "member"]
    joined_at: datetime


class HouseholdMembersResponse(BaseModel):
    members: list[HouseholdMemberItem]


class HouseholdCareContextResponse(BaseModel):
    viewer_user_id: str
    subject_user_id: str
    household_id: str


class HouseholdCareMembersResponse(BaseModel):
    viewer_user_id: str
    household_id: str
    members: list[HouseholdMemberItem]


class HouseholdBundleResponse(BaseModel):
    household: HouseholdResponse | None
    members: list[HouseholdMemberItem]
    active_household_id: str | None = None


class HouseholdInviteResponseItem(BaseModel):
    invite_id: str
    household_id: str
    code: str
    created_by_user_id: str
    created_at: datetime
    expires_at: datetime
    max_uses: int
    uses: int


class HouseholdInviteCreateResponse(BaseModel):
    invite: HouseholdInviteResponseItem


class HouseholdJoinRequest(BaseModel):
    code: str


class HouseholdActiveUpdateRequest(BaseModel):
    household_id: str | None


class HouseholdActiveUpdateResponse(BaseModel):
    ok: bool = True
    active_household_id: str | None = None


class HouseholdLeaveResponse(BaseModel):
    ok: bool = True
    left_household_id: str


class HouseholdMemberRemoveResponse(BaseModel):
    ok: bool = True
    removed_user_id: str


class HouseholdCareProfileResponse(BaseModel):
    context: HouseholdCareContextResponse
    profile: HealthProfileResponseItem


class HouseholdCareMealSummaryResponse(BaseModel):
    context: HouseholdCareContextResponse
    summary: MealDailySummaryResponse


class HouseholdCareReminderListResponse(BaseModel):
    context: HouseholdCareContextResponse
    reminders: list[ReminderEvent] = Field(default_factory=list)
    metrics: EngagementMetrics = Field(
        default_factory=lambda: EngagementMetrics(
            reminders_sent=0,
            meal_confirmed_yes=0,
            meal_confirmed_no=0,
            meal_confirmation_rate=0.0,
        )
    )
