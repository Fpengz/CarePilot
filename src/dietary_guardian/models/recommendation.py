from pydantic import BaseModel, Field


class RecommendationOutput(BaseModel):
    safe: bool
    rationale: str
    localized_advice: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    evidence: dict[str, float] = Field(default_factory=dict)
