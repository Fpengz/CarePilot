"""
Compose application settings and environment bootstrap helpers.

This module loads, validates, and exposes the top-level configuration
used across the runtime.
"""

from __future__ import annotations

from functools import lru_cache
from typing import ClassVar, Literal

from pydantic import ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from care_pilot.config.llm import LLMSettings
from care_pilot.config.runtime import (
    APISettings,
    AuthSettings,
    ChannelSettings,
    ChatSettings,
    EmotionSettings,
    FeatureFlags,
    MemorySettings,
    ObservabilitySettings,
    StorageSettings,
    WorkerSettings,
)


class AppIdentitySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_", extra="ignore", case_sensitive=False, populate_by_name=True
    )

    env: Literal["dev", "staging", "prod"] = Field(default="dev")
    timezone: str = "Asia/Singapore"
    image_downscale_enabled: bool = False
    image_max_side_px: int = Field(default=1024, ge=256, le=4096)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    _DEFAULT_SESSION_SECRET: ClassVar[str] = "dev-insecure-session-secret-change-me"

    app: AppIdentitySettings = Field(default_factory=AppIdentitySettings)
    api: APISettings = Field(default_factory=APISettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    chat: ChatSettings = Field(default_factory=ChatSettings)
    channels: ChannelSettings = Field(default_factory=ChannelSettings)
    emotion: EmotionSettings = Field(default_factory=EmotionSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    workers: WorkerSettings = Field(default_factory=WorkerSettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    @model_validator(mode="after")
    def normalize_and_validate(self) -> AppSettings:
        # Provider credential checks are enforced in LLMSettings._validate_provider_credentials.
        # Capability key/type checks are enforced by the dict[LLMCapability, ...] annotation.
        # This validator handles cross-group (multi-section) business rules only.

        if self.observability.readiness_fail_on_warnings is None:
            self.observability.readiness_fail_on_warnings = self.app.env in {
                "staging",
                "prod",
            }

        if not self.auth.session_secret:
            raise ValueError("SESSION_SECRET must not be empty")

        if self.app.env != "dev" and self.auth.seed_demo_users:
            # If they explicitly set it to True in non-dev, it's an error.
            # If it's the default, we flip it to False.
            # Actually, the test expects a ValidationError if set to True in prod.
            if "AUTH_SEED_DEMO_USERS" in self.auth.model_dump(
                exclude_unset=True
            ) or "seed_demo_users" in self.auth.model_dump(exclude_unset=True):
                raise ValueError("seed_demo_users must be False for non-dev environments")
            self.auth.seed_demo_users = False

        if self.app.env == "prod" and self.workers.tool_policy_enforcement_mode == "shadow":
            self.workers.tool_policy_enforcement_mode = "enforce"
        if self.app.env in {"staging", "prod"}:
            if self.auth.session_secret == self._DEFAULT_SESSION_SECRET:
                raise ValueError("SESSION_SECRET must be overridden for staging/prod")
            if not self.auth.cookie_secure:
                raise ValueError("COOKIE_SECURE must be enabled for staging/prod")
        if self.auth.cookie_samesite == "none" and not self.auth.cookie_secure:
            raise ValueError("COOKIE_SECURE must be enabled when COOKIE_SAMESITE=none")
        if self.storage.ephemeral_state_backend == "redis" and not self.storage.redis_url:
            raise ValueError("REDIS_URL must be set when EPHEMERAL_STATE_BACKEND=redis")
        if (
            self.workers.worker_mode == "external"
            and self.storage.ephemeral_state_backend != "redis"
        ):
            raise ValueError("EPHEMERAL_STATE_BACKEND must be redis when WORKER_MODE=external")
        return self

    @property
    def effective_google_api_key(self) -> str | None:
        return self.llm.effective_google_api_key

    @classmethod
    def from_environment(cls) -> AppSettings:
        return cls()


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    # load_dotenv() is not strictly needed with pydantic-settings if env_file is configured,
    # but we keep it for now or rely on pydantic-settings env_file feature.
    return AppSettings()
