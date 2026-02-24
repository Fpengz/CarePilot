from typing import Literal

from pydantic import BaseModel, Field


class MedicalConfig(BaseModel):
    sodium_limit_mg: int = Field(
        default=2000, gt=0, description="Max daily sodium for Hypertension"
    )
    sugar_alert_threshold: float = Field(
        default=5.5, gt=0, description="HbA1c threshold for monitoring"
    )


class ModelSettings(BaseModel):
    primary_model: str = "gemini-3-flash"
    fallback_model: str = "gemini-3.1-pro"
    retry_limit: int = Field(default=3, ge=0)
    clarification_threshold: float = Field(default=0.75, ge=0.0, le=1.0)


class LocalModelProfile(BaseModel):
    id: str
    provider: Literal["ollama", "vllm"]
    model_name: str
    base_url: str
    api_key_env: str = "LOCAL_LLM_API_KEY"
    enabled: bool = True


def _default_local_profiles() -> dict[str, LocalModelProfile]:
    return {
        "ollama_qwen3-vl:4b": LocalModelProfile(
            id="ollama_qwen3-vl:4b",
            provider="ollama",
            model_name="qwen3-vl:4b",
            base_url="http://localhost:11434/v1",
            api_key_env="LOCAL_LLM_API_KEY",
            enabled=True,
        ),
        "vllm_qwen": LocalModelProfile(
            id="vllm_qwen",
            provider="vllm",
            model_name="Qwen/Qwen2.5-7B-Instruct",
            base_url="http://localhost:8000/v1",
            api_key_env="LOCAL_LLM_API_KEY",
            enabled=True,
        ),
    }


class LocalModelSettings(BaseModel):
    profiles: dict[str, LocalModelProfile] = Field(default_factory=_default_local_profiles)


class AppConfig(BaseModel):
    medical: MedicalConfig = Field(default_factory=MedicalConfig)
    models: ModelSettings = Field(default_factory=ModelSettings)
    local_models: LocalModelSettings = Field(default_factory=LocalModelSettings)
