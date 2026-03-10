"""Legacy runtime config compatibility models and local-model defaults."""

from pydantic import BaseModel, Field

from dietary_guardian.config.llm import LocalModelProfile, default_local_profiles


class MedicalConfig(BaseModel):
    sodium_limit_mg: int = Field(default=2000, gt=0, description="Max daily sodium for Hypertension")
    sugar_alert_threshold: float = Field(default=5.5, gt=0, description="HbA1c threshold for monitoring")


class ModelSettings(BaseModel):
    primary_model: str = "gemini-3-flash"
    fallback_model: str = "gemini-3.1-pro"
    retry_limit: int = Field(default=3, ge=0)
    clarification_threshold: float = Field(default=0.75, ge=0.0, le=1.0)


class LocalModelSettings(BaseModel):
    profiles: dict[str, LocalModelProfile] = Field(default_factory=default_local_profiles)


class AppConfig(BaseModel):
    medical: MedicalConfig = Field(default_factory=MedicalConfig)
    models: ModelSettings = Field(default_factory=ModelSettings)
    local_models: LocalModelSettings = Field(default_factory=LocalModelSettings)
