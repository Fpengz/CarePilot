"""
Define role tool data models.

This module contains role tool models used by profile tooling workflows.
"""

from pydantic import BaseModel, Field


class RoleToolContract(BaseModel):
    role: str
    allowed_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)
    notes: str | None = None


class AgentRoleToolContract(BaseModel):
    agent_id: str
    contracts: list[RoleToolContract] = Field(default_factory=list)
