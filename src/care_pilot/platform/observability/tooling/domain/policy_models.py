"""Tool authorization policy domain models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from care_pilot.features.profiles.domain.models import AccountRole

ToolPolicyEffect = Literal["allow", "deny"]


class ToolRolePolicyRecord(BaseModel):
    id: str
    role: AccountRole
    agent_id: str
    tool_name: str
    effect: ToolPolicyEffect
    conditions: dict[str, object] = Field(default_factory=dict)
    priority: int = 0
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
