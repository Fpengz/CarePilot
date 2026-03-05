from pydantic import BaseModel, Field


class HealthProfileOnboardingStepDefinition(BaseModel):
    id: str
    title: str
    description: str
    fields: list[str] = Field(default_factory=list)


class HealthProfileOnboardingState(BaseModel):
    user_id: str
    current_step: str = "basic_identity"
    completed_steps: list[str] = Field(default_factory=list)
    is_complete: bool = False
    updated_at: str | None = None
