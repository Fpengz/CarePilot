"""Typed LLM provider, capability, and model-profile configuration contracts.

This module defines the hierarchical LLM configuration used throughout the
care_pilot system.  Provider credentials and network parameters are
grouped into typed value objects (GeminiConfig, OpenAIConfig, LocalLLMConfig,
InferenceConfig) that are composed by the top-level LLMSettings via @property
accessors.  All env-var reading happens at the LLMSettings level so that
pydantic-settings source resolution stays in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelProvider(StrEnum):
    GEMINI = "gemini"
    OPENAI = "openai"
    QWEN = "qwen"
    OLLAMA = "ollama"
    VLLM = "vllm"
    CODEX = "codex"
    TEST = "test"


class LLMCapability(StrEnum):
    CHATBOT = "chatbot"
    MEAL_VISION = "meal_vision"
    DIETARY_REASONING = "dietary_reasoning"
    MEDICATION_PARSE = "medication_parse"
    REPORT_PARSE = "report_parse"
    CLINICAL_SUMMARY = "clinical_summary"
    FALLBACK = "fallback"


class LLMCapabilityTarget(BaseModel):
    """Per-capability routing override: provider, model, endpoint, and credentials.

    This is inline configuration data (not read from env vars), so it derives
    from BaseModel rather than BaseSettings.
    """

    provider: ModelProvider
    model: str | None = None
    base_url: AnyHttpUrl | str | None = None
    api_key: str | None = None
    api_key_env: str | None = None


class LocalModelProfile(BaseModel):
    """Named local model profile for Ollama/vLLM providers.

    Stored in LLMSettings.local_profiles and referenced by LLMFactory.from_profile().
    Derives from BaseModel (not BaseSettings) because profiles are defined in
    code, not read from env vars.
    """

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


# ---------------------------------------------------------------------------
# Typed provider config value objects
# These are immutable views over the flat LLMSettings fields, grouped by
# concern.  Consuming code should prefer these over direct flat-field access.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GeminiConfig:
    """Google Gemini credentials and model defaults."""

    api_key: str | None
    google_api_key: str | None
    model: str

    @property
    def effective_api_key(self) -> str | None:
        """Return whichever Google/Gemini key is available."""
        return self.google_api_key or self.api_key


@dataclass(frozen=True)
class OpenAIConfig:
    """OpenAI credentials, model defaults, and network parameters."""

    api_key: str | None
    model: str
    base_url: str | None
    request_timeout_seconds: float
    transport_max_retries: int


@dataclass(frozen=True)
class QwenConfig:
    """Qwen OpenAI-compatible credentials, model defaults, and network parameters."""

    api_key: str | None
    model: str
    base_url: str | None


@dataclass(frozen=True)
class LocalLLMConfig:
    """Local LLM (Ollama/vLLM) credentials, model defaults, network parameters, and named profiles."""

    base_url: str | None
    api_key: str
    model: str
    request_timeout_seconds: float
    transport_max_retries: int
    profiles: dict  # dict[str, LocalModelProfile]


@dataclass(frozen=True)
class InferenceConfig:
    """LLM inference engine runtime parameters."""

    wall_clock_timeout_seconds: float
    cloud_output_validation_retries: int
    local_output_validation_retries: int
    use_engine_v2: bool


class LLMSettings(BaseSettings):
    """Top-level LLM configuration: provider selection, capability routing, and per-provider settings.

    All env-var reading is centralised here.  Use the typed properties (`.gemini`,
    `.openai`, `.local`, `.inference`) for structured access in application code.

    Environment variable mapping (case-insensitive):
      LLM_PROVIDER, LLM_DEFAULT_CAPABILITY, LLM_CAPABILITY_TARGETS,
      REQUIRED_PROVIDER, GEMINI_API_KEY, GOOGLE_API_KEY, GEMINI_MODEL,
      OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL,
      QWEN_API_KEY, QWEN_MODEL, QWEN_BASE_URL,
      OPENAI_REQUEST_TIMEOUT_SECONDS, OPENAI_TRANSPORT_MAX_RETRIES,
      LOCAL_LLM_BASE_URL, LOCAL_LLM_API_KEY, LOCAL_LLM_MODEL,
      LOCAL_LLM_REQUEST_TIMEOUT_SECONDS, LOCAL_LLM_TRANSPORT_MAX_RETRIES,
      LLM_INFERENCE_WALL_CLOCK_TIMEOUT_SECONDS,
      LLM_CLOUD_OUTPUT_VALIDATION_RETRIES, LLM_LOCAL_OUTPUT_VALIDATION_RETRIES,
      LLM_USE_INFERENCE_ENGINE_V2
    """

    model_config = SettingsConfigDict(
        extra="ignore", case_sensitive=False, populate_by_name=True
    )

    # --- Core routing ---
    provider: ModelProvider = Field(
        default=ModelProvider.TEST, validation_alias="LLM_PROVIDER"
    )
    default_capability: LLMCapability = Field(
        default=LLMCapability.DIETARY_REASONING,
        validation_alias="LLM_DEFAULT_CAPABILITY",
    )
    capability_map: dict[LLMCapability, LLMCapabilityTarget] = Field(
        default_factory=dict, validation_alias="LLM_CAPABILITY_TARGETS"
    )
    required_provider: ModelProvider | None = Field(
        default=None, validation_alias="REQUIRED_PROVIDER"
    )

    # --- Google Gemini ---
    gemini_api_key: str | None = None
    google_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"

    # --- OpenAI ---
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: AnyHttpUrl | str | None = None
    openai_request_timeout_seconds: float = Field(
        default=120.0, ge=1.0, le=7200.0
    )
    openai_transport_max_retries: int = Field(default=2, ge=0, le=10)

    # --- Qwen (OpenAI-compatible) ---
    qwen_api_key: str | None = None
    qwen_model: str = "qwen-vl-cheapest"
    qwen_base_url: AnyHttpUrl | str | None = (
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )

    # --- Local LLM (Ollama / vLLM) ---
    local_llm_base_url: AnyHttpUrl | str | None = "http://localhost:11434/v1"
    local_llm_api_key: str = "ollama"
    local_llm_model: str = "qwen3-vl:4b"
    local_llm_request_timeout_seconds: float = Field(
        default=1200.0, ge=1.0, le=7200.0
    )
    local_llm_transport_max_retries: int = Field(default=0, ge=0, le=10)
    local_profiles: dict[str, LocalModelProfile] = Field(
        default_factory=default_local_profiles
    )

    # --- Inference engine ---
    inference_wall_clock_timeout_seconds: float = Field(
        default=180.0,
        ge=0.1,
        le=3600.0,
        validation_alias="LLM_INFERENCE_WALL_CLOCK_TIMEOUT_SECONDS",
    )
    cloud_output_validation_retries: int = Field(
        default=1,
        ge=0,
        le=5,
        validation_alias="LLM_CLOUD_OUTPUT_VALIDATION_RETRIES",
    )
    local_output_validation_retries: int = Field(
        default=0,
        ge=0,
        le=5,
        validation_alias="LLM_LOCAL_OUTPUT_VALIDATION_RETRIES",
    )
    use_inference_engine_v2: bool = Field(
        default=True, validation_alias="LLM_USE_INFERENCE_ENGINE_V2"
    )

    # ---------------------------------------------------------------------------
    # Typed provider config views (preferred access pattern for consuming code)
    # ---------------------------------------------------------------------------

    @property
    def gemini(self) -> GeminiConfig:
        """Structured view of Gemini credentials and model defaults."""
        return GeminiConfig(
            api_key=self.gemini_api_key,
            google_api_key=self.google_api_key,
            model=self.gemini_model,
        )

    @property
    def openai(self) -> OpenAIConfig:
        """Structured view of OpenAI credentials and network settings."""
        return OpenAIConfig(
            api_key=self.openai_api_key,
            model=self.openai_model,
            base_url=(
                str(self.openai_base_url) if self.openai_base_url else None
            ),
            request_timeout_seconds=self.openai_request_timeout_seconds,
            transport_max_retries=self.openai_transport_max_retries,
        )

    @property
    def qwen(self) -> QwenConfig:
        """Structured view of Qwen credentials and model defaults."""
        return QwenConfig(
            api_key=self.qwen_api_key,
            model=self.qwen_model,
            base_url=str(self.qwen_base_url) if self.qwen_base_url else None,
        )

    @property
    def local(self) -> LocalLLMConfig:
        """Structured view of local LLM credentials, network settings, and profiles."""
        return LocalLLMConfig(
            base_url=(
                str(self.local_llm_base_url)
                if self.local_llm_base_url
                else None
            ),
            api_key=self.local_llm_api_key,
            model=self.local_llm_model,
            request_timeout_seconds=self.local_llm_request_timeout_seconds,
            transport_max_retries=self.local_llm_transport_max_retries,
            profiles=self.local_profiles,
        )

    @property
    def inference(self) -> InferenceConfig:
        """Structured view of inference engine runtime parameters."""
        return InferenceConfig(
            wall_clock_timeout_seconds=self.inference_wall_clock_timeout_seconds,
            cloud_output_validation_retries=self.cloud_output_validation_retries,
            local_output_validation_retries=self.local_output_validation_retries,
            use_engine_v2=self.use_inference_engine_v2,
        )

    @property
    def effective_google_api_key(self) -> str | None:
        """Convenience alias for AppSettings compatibility; delegates to gemini.effective_api_key."""
        return self.gemini.effective_api_key

    @model_validator(mode="after")
    def _validate_provider_credentials(self) -> "LLMSettings":
        """Enforce that each non-test provider has required credentials or endpoints."""
        if (
            self.provider == ModelProvider.GEMINI
            and not self.gemini.effective_api_key
        ):
            raise ValueError(
                "Gemini provider selected but GEMINI_API_KEY/GOOGLE_API_KEY is not set"
            )
        if self.provider == ModelProvider.OPENAI and not self.openai.api_key:
            raise ValueError(
                "OpenAI provider selected but OPENAI_API_KEY is not set"
            )
        if self.provider == ModelProvider.QWEN and not self.qwen.api_key:
            raise ValueError(
                "Qwen provider selected but QWEN_API_KEY is not set"
            )
        if self.provider == ModelProvider.CODEX:
            raise ValueError(
                "Codex provider routing is reserved but not implemented yet"
            )
        if (
            self.provider in {ModelProvider.OLLAMA, ModelProvider.VLLM}
            and not self.local.base_url
        ):
            raise ValueError(
                "Local provider selected but LOCAL_LLM_BASE_URL is not set"
            )
        return self
