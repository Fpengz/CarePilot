"""Typed LLM provider, capability, and model-profile configuration contracts."""

from enum import StrEnum
from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelProvider(StrEnum):
    GEMINI = "gemini"
    OPENAI = "openai"
    OLLAMA = "ollama"
    VLLM = "vllm"
    CODEX = "codex"
    TEST = "test"


class LLMCapability(StrEnum):
    CHATBOT = "chatbot"
    MEAL_VISION = "meal_vision"
    DIETARY_REASONING = "dietary_reasoning"
    REPORT_PARSE = "report_parse"
    CLINICAL_SUMMARY = "clinical_summary"
    FALLBACK = "fallback"


class LLMCapabilityTarget(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, populate_by_name=True)

    provider: Literal["gemini", "openai", "ollama", "vllm", "codex", "test"]
    model: str | None = None
    base_url: AnyHttpUrl | str | None = None
    api_key: str | None = None
    api_key_env: str | None = None


class LocalModelProfile(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, populate_by_name=True)

    id: str
    provider: Literal["ollama", "vllm"]
    model_name: str
    base_url: str
    api_key_env: str = "LOCAL_LLM_API_KEY"
    enabled: bool = True



def default_local_profiles() -> dict[str, LocalModelProfile]:
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


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, populate_by_name=True)

    provider: Literal["gemini", "openai", "ollama", "vllm", "codex", "test"] = Field(default="test", validation_alias="LLM_PROVIDER")
    default_capability: str = Field(default=LLMCapability.DIETARY_REASONING.value, validation_alias="LLM_DEFAULT_CAPABILITY")
    capability_targets: dict[str, LLMCapabilityTarget] = Field(default_factory=dict, validation_alias="LLM_CAPABILITY_TARGETS")
    required_provider: Literal["gemini", "openai", "ollama", "vllm", "codex", "test"] | None = Field(default=None, validation_alias="REQUIRED_PROVIDER")
    gemini_api_key: str | None = None
    google_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: AnyHttpUrl | str | None = None
    openai_request_timeout_seconds: float = Field(default=120.0, ge=1.0, le=7200.0)
    openai_transport_max_retries: int = Field(default=2, ge=0, le=10)
    local_llm_base_url: AnyHttpUrl | str | None = "http://localhost:11434/v1"
    local_llm_api_key: str = "ollama"
    local_llm_model: str = "qwen3-vl:4b"
    local_llm_request_timeout_seconds: float = Field(default=1200.0, ge=1.0, le=7200.0)
    local_llm_transport_max_retries: int = Field(default=0, ge=0, le=10)
    cloud_output_validation_retries: int = Field(default=1, ge=0, le=5)
    local_output_validation_retries: int = Field(default=0, ge=0, le=5)
    inference_wall_clock_timeout_seconds: float = Field(default=180.0, ge=0.1, le=3600.0, validation_alias="LLM_INFERENCE_WALL_CLOCK_TIMEOUT_SECONDS")
    use_inference_engine_v2: bool = True
    local_profiles: dict[str, LocalModelProfile] = Field(default_factory=default_local_profiles)

    @property
    def effective_google_api_key(self) -> str | None:
        return self.google_api_key or self.gemini_api_key
