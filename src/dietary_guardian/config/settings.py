from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: Literal["gemini", "ollama", "vllm", "test"] = "test"
    gemini_api_key: str | None = None
    google_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"

    local_llm_base_url: AnyHttpUrl | str | None = "http://localhost:11434/v1"
    local_llm_api_key: str = "ollama"
    local_llm_model: str = "qwen3-vl:4b"
    ollama_base_url: AnyHttpUrl | str | None = "http://localhost:11434/v1"
    local_llm_request_timeout_seconds: float = Field(default=1200.0, ge=1.0, le=7200.0)
    local_llm_transport_max_retries: int = Field(default=0, ge=0, le=10)

    dietary_guardian_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    app_timezone: str = "Asia/Singapore"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8001, ge=1, le=65535)
    api_cors_origins: str = "http://localhost:3000"
    session_secret: str = "dev-insecure-session-secret-change-me"
    cookie_secure: bool = False
    auth_password_hash_scheme: str = "pbkdf2_sha256"
    auth_session_ttl_seconds: int = Field(default=86400, ge=1, le=60 * 60 * 24 * 30)
    auth_login_max_failed_attempts: int = Field(default=5, ge=1, le=20)
    auth_login_failure_window_seconds: int = Field(default=300, ge=1, le=3600)
    auth_login_lockout_seconds: int = Field(default=300, ge=1, le=86400)
    auth_audit_events_max_entries: int = Field(default=500, ge=10, le=10000)
    workflow_trace_persistence_enabled: bool = False

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_dev_mode: bool = True
    telegram_request_timeout_seconds: float = Field(default=10.0, ge=1.0, le=300.0)

    use_inference_engine_v2: bool = True
    use_alert_outbox_v2: bool = True
    alert_worker_max_attempts: int = 3
    alert_worker_concurrency: int = 4
    cloud_output_validation_retries: int = Field(default=1, ge=0, le=5)
    local_output_validation_retries: int = Field(default=0, ge=0, le=5)

    image_downscale_enabled: bool = False
    image_max_side_px: int = Field(default=1024, ge=256, le=4096)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @model_validator(mode="after")
    def normalize_and_validate(self) -> "Settings":
        if self.llm_provider in {"ollama", "vllm"} and not self.local_llm_base_url:
            self.local_llm_base_url = self.ollama_base_url

        if self.llm_provider == "gemini" and not (self.gemini_api_key or self.google_api_key):
            raise ValueError(
                "Gemini provider selected but GEMINI_API_KEY/GOOGLE_API_KEY is not set"
            )

        if self.llm_provider in {"ollama", "vllm"} and not self.local_llm_base_url:
            raise ValueError(
                "Local provider selected but LOCAL_LLM_BASE_URL/OLLAMA_BASE_URL is not set"
            )
        if not self.session_secret:
            raise ValueError("SESSION_SECRET must not be empty")

        return self

    @property
    def effective_google_api_key(self) -> str | None:
        return self.google_api_key or self.gemini_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings()
