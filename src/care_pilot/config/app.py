"""
Compose application settings and environment bootstrap helpers.

This module loads, validates, and exposes the top-level configuration
used across the runtime.
"""

from __future__ import annotations

from functools import lru_cache
from typing import ClassVar, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, model_validator

from care_pilot.config.llm import LLMSettings
from care_pilot.config.runtime import (
    APISettings,
    AuthSettings,
    ChatSettings,
    ChannelSettings,
    EmotionSettings,
    MemorySettings,
    ObservabilitySettings,
    StorageSettings,
    WorkerSettings,
)


class AppIdentitySettings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    env: Literal["dev", "staging", "prod"] = Field(default="dev", validation_alias="APP_ENV")
    timezone: str = Field(default="Asia/Singapore", validation_alias="APP_TIMEZONE")
    image_downscale_enabled: bool = Field(default=False, validation_alias="IMAGE_DOWNSCALE_ENABLED")
    image_max_side_px: int = Field(
        default=1024, ge=256, le=4096, validation_alias="IMAGE_MAX_SIDE_PX"
    )


class AppSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

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

    @model_validator(mode="after")
    def normalize_and_validate(self) -> "AppSettings":
        # Provider credential checks are enforced in LLMSettings._validate_provider_credentials.
        # Capability key/type checks are enforced by the dict[LLMCapability, ...] annotation.
        # This validator handles cross-group (multi-section) business rules only.

        if self.observability.readiness_fail_on_warnings is None:
            self.observability.readiness_fail_on_warnings = self.app.env in {
                "staging",
                "prod",
            }
        if self.auth.seed_demo_users is None:
            self.auth.seed_demo_users = self.app.env == "dev"

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
    def from_environment(cls) -> "AppSettings":
        return cls(
            app=AppIdentitySettings(),
            api=APISettings(),
            auth=AuthSettings(),
            chat=ChatSettings(),
            channels=ChannelSettings(),
            emotion=EmotionSettings(),
            llm=LLMSettings(),
            memory=MemorySettings(),
            observability=ObservabilitySettings(),
            storage=StorageSettings(),
            workers=WorkerSettings(),
        )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    load_dotenv()
    return AppSettings.from_environment()
