"""
Define the dietary reasoning agent schemas.

These schemas are generic and should not depend on feature domain models.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DietaryAgentInput(BaseModel):
    """Generic input for dietary safety and reasoning requests."""

    user_name: str
    health_goals: list[str] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list)
    meal_name: str
    ingredients: list[str] = Field(default_factory=list)
    portion_size: str | None = None
    is_safe: bool = True
    safety_warnings: list[str] = Field(default_factory=list)


class DietaryAgentOutput(BaseModel):
    """Structured output from the dietary reasoning agent."""

    analysis: str
    advice: str
    is_safe: bool
    warnings: list[str] = Field(default_factory=list)


__all__ = ["DietaryAgentInput", "DietaryAgentOutput"]
