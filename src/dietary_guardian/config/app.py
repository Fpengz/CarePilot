"""Composed application settings and environment bootstrap entry points."""

from __future__ import annotations

from functools import lru_cache
from typing import ClassVar, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, model_validator

from dietary_guardian.config.api import APISettings
from dietary_guardian.config.auth import AuthSettings
from dietary_guardian.config.channels import ChannelSettings
from dietary_guardian.config.emotion import EmotionSettings
from dietary_guardian.config.llm import LLMCapability, LLMSettings
from dietary_guardian.config.observability import ObservabilitySettings
from dietary_guardian.config.storage import StorageSettings
from dietary_guardian.config.workers import WorkerSettings


class AppIdentitySettings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    env: Literal["dev", "staging", "prod"] = Field(default="dev", validation_alias="APP_ENV")
    timezone: str = Field(default="Asia/Singapore", validation_alias="APP_TIMEZONE")
    image_downscale_enabled: bool = Field(default=False, validation_alias="IMAGE_DOWNSCALE_ENABLED")
    image_max_side_px: int = Field(default=1024, ge=256, le=4096, validation_alias="IMAGE_MAX_SIDE_PX")

class AppSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    _DEFAULT_SESSION_SECRET: ClassVar[str] = "dev-insecure-session-secret-change-me"

    app: AppIdentitySettings = Field(default_factory=AppIdentitySettings)
    api: APISettings = Field(default_factory=APISettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    channels: ChannelSettings = Field(default_factory=ChannelSettings)
    emotion: EmotionSettings = Field(default_factory=EmotionSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    workers: WorkerSettings = Field(default_factory=WorkerSettings)

    @model_validator(mode="after")
    def normalize_and_validate(self) -> "AppSettings":
        valid_capabilities = {item.value for item in LLMCapability}
        invalid_capabilities = sorted(set(self.llm.capability_targets) - valid_capabilities)
        if invalid_capabilities:
            joined = ", ".join(invalid_capabilities)
            raise ValueError(f"LLM_CAPABILITY_TARGETS contains unsupported capability keys: {joined}")

        if self.llm.default_capability not in valid_capabilities:
            raise ValueError(f"LLM_DEFAULT_CAPABILITY must be one of: {', '.join(sorted(valid_capabilities))}")

        if self.observability.readiness_fail_on_warnings is None:
            self.observability.readiness_fail_on_warnings = self.app.env in {"staging", "prod"}
        if self.auth.seed_demo_users is None:
            self.auth.seed_demo_users = self.app.env == "dev"

        if self.llm.provider == "gemini" and not (self.llm.gemini_api_key or self.llm.google_api_key):
            raise ValueError("Gemini provider selected but GEMINI_API_KEY/GOOGLE_API_KEY is not set")
        if self.llm.provider == "openai" and not self.llm.openai_api_key:
            raise ValueError("OpenAI provider selected but OPENAI_API_KEY is not set")
        if self.llm.provider == "codex":
            raise ValueError("Codex provider routing is reserved but not implemented yet")
        if self.llm.provider in {"ollama", "vllm"} and not self.llm.local_llm_base_url:
            raise ValueError("Local provider selected but LOCAL_LLM_BASE_URL is not set")
        if not self.auth.session_secret:
            raise ValueError("SESSION_SECRET must not be empty")

        if self.app.env == "prod" and self.workers.tool_policy_enforcement_mode == "shadow":
            self.workers.tool_policy_enforcement_mode = "enforce"
        if self.app.env in {"staging", "prod"}:
            if self.auth.session_secret == self._DEFAULT_SESSION_SECRET:
                raise ValueError("SESSION_SECRET must be overridden for staging/prod")
            if not self.auth.cookie_secure:
                raise ValueError("COOKIE_SECURE must be enabled for staging/prod")
            if self.auth.seed_demo_users:
                raise ValueError("AUTH_SEED_DEMO_USERS must be disabled for staging/prod")
        if self.auth.cookie_samesite == "none" and not self.auth.cookie_secure:
            raise ValueError("COOKIE_SECURE must be enabled when COOKIE_SAMESITE=none")
        if self.storage.ephemeral_state_backend == "redis" and not self.storage.redis_url:
            raise ValueError("REDIS_URL must be set when EPHEMERAL_STATE_BACKEND=redis")
        if self.workers.worker_mode == "external" and self.storage.ephemeral_state_backend != "redis":
            raise ValueError("EPHEMERAL_STATE_BACKEND must be redis when WORKER_MODE=external")
        return self

    @property
    def effective_google_api_key(self) -> str | None:
        return self.llm.effective_google_api_key

    @classmethod
    def from_environment(cls) -> "AppSettings":
        return cls(
            app=AppIdentitySettings(),
            api=APISettings(),
            auth=AuthSettings(),
            channels=ChannelSettings(),
            emotion=EmotionSettings(),
            llm=LLMSettings(),
            observability=ObservabilitySettings(),
            storage=StorageSettings(),
            workers=WorkerSettings(),
        )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    load_dotenv()
    return AppSettings.from_environment()
