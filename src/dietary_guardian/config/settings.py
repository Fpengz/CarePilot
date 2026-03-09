from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    _DEFAULT_SESSION_SECRET = "dev-insecure-session-secret-change-me"

    app_env: Literal["dev", "staging", "prod"] = "dev"
    app_data_backend: Literal["sqlite", "postgres"] = "sqlite"
    llm_provider: Literal["gemini", "openai", "ollama", "vllm", "test"] = "test"
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

    dietary_guardian_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    app_timezone: str = "Asia/Singapore"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8001, ge=1, le=65535)
    api_cors_origins: str = "http://localhost:3000"
    api_cors_methods: str = "GET,POST,PATCH,DELETE,OPTIONS"
    api_cors_headers: str = "Content-Type,X-Requested-With,Authorization"
    api_meal_upload_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=50 * 1024 * 1024)
    api_rate_limit_enabled: bool = True
    api_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    api_rate_limit_auth_login_max_requests: int = Field(default=20, ge=1, le=500)
    api_rate_limit_meal_analyze_max_requests: int = Field(default=20, ge=1, le=500)
    api_rate_limit_recommendations_generate_max_requests: int = Field(default=10, ge=1, le=500)
    emotion_inference_enabled: bool = False
    emotion_speech_enabled: bool = False
    emotion_request_timeout_seconds: float = Field(default=15.0, ge=0.1, le=300.0)
    emotion_model_device: Literal["auto", "cpu", "cuda"] = "auto"
    emotion_text_model_id: str = "j-hartmann/emotion-english-distilroberta-base"
    emotion_speech_model_id: str = "meralion/speech-emotion-recognition"
    emotion_source_commit: str = "9afc3f1a3a3fec71a4e5920d8f4103710b337ecc"
    api_dev_log_verbose: bool = False
    api_dev_log_headers: bool = False
    api_dev_log_response_headers: bool = False
    session_secret: str = _DEFAULT_SESSION_SECRET
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_password_hash_scheme: str = "pbkdf2_sha256"
    api_sqlite_db_path: str = "dietary_guardian_api.db"
    auth_store_backend: Literal["in_memory", "sqlite", "postgres"] = "sqlite"
    auth_sqlite_db_path: str = "dietary_guardian_auth.db"
    household_store_backend: Literal["sqlite", "postgres"] = "sqlite"
    postgres_dsn: str | None = None
    postgres_pool_min_size: int = Field(default=1, ge=1, le=20)
    postgres_pool_max_size: int = Field(default=5, ge=1, le=50)
    postgres_statement_timeout_ms: int = Field(default=5000, ge=1, le=600000)
    ephemeral_state_backend: Literal["in_memory", "redis"] = "in_memory"
    redis_url: str | None = None
    redis_namespace: str = "dietary_guardian"
    redis_default_ttl_seconds: int = Field(default=300, ge=1, le=86400)
    redis_lock_ttl_seconds: int = Field(default=30, ge=1, le=3600)
    redis_worker_signal_channel: str = "workers.ready"
    readiness_fail_on_warnings: bool | None = None
    required_provider: Literal["gemini", "openai", "ollama", "vllm", "test"] | None = None
    auth_session_ttl_seconds: int = Field(default=86400, ge=1, le=60 * 60 * 24 * 30)
    auth_login_max_failed_attempts: int = Field(default=5, ge=1, le=20)
    auth_login_failure_window_seconds: int = Field(default=300, ge=1, le=3600)
    auth_login_lockout_seconds: int = Field(default=300, ge=1, le=86400)
    auth_audit_events_max_entries: int = Field(default=500, ge=10, le=10000)
    auth_seed_demo_users: bool | None = None
    auth_demo_member_password: str = "member-pass"
    auth_demo_helper_password: str = "helper-pass"
    auth_demo_admin_password: str = "admin-pass"
    workflow_trace_persistence_enabled: bool = False
    tool_policy_enforcement_mode: Literal["shadow", "enforce"] = "shadow"
    workflow_contract_bootstrap: bool = True

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_dev_mode: bool = True
    telegram_request_timeout_seconds: float = Field(default=10.0, ge=1.0, le=300.0)
    email_dev_mode: bool = True
    email_smtp_host: str | None = None
    email_smtp_port: int = Field(default=587, ge=1, le=65535)
    email_smtp_username: str | None = None
    email_smtp_password: str | None = None
    email_smtp_use_tls: bool = True
    email_from_address: str = "noreply@dietary-guardian.local"
    sms_dev_mode: bool = True
    sms_webhook_url: AnyHttpUrl | str | None = None
    sms_api_key: str | None = None
    sms_sender_id: str = "DietaryGuardian"
    reminder_scheduler_interval_seconds: int = Field(default=30, ge=5, le=3600)
    reminder_scheduler_batch_size: int = Field(default=100, ge=1, le=1000)
    worker_mode: Literal["in_process", "external"] = "in_process"
    reminder_worker_poll_interval_seconds: int = Field(default=15, ge=1, le=3600)
    outbox_worker_poll_interval_seconds: int = Field(default=5, ge=1, le=3600)

    use_inference_engine_v2: bool = True
    use_alert_outbox_v2: bool = True
    alert_worker_max_attempts: int = 3
    alert_worker_concurrency: int = 4
    cloud_output_validation_retries: int = Field(default=1, ge=0, le=5)
    local_output_validation_retries: int = Field(default=0, ge=0, le=5)
    llm_inference_wall_clock_timeout_seconds: float = Field(default=180.0, ge=0.1, le=3600.0)

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
        if self.readiness_fail_on_warnings is None:
            self.readiness_fail_on_warnings = self.app_env in {"staging", "prod"}

        if self.llm_provider == "gemini" and not (self.gemini_api_key or self.google_api_key):
            raise ValueError(
                "Gemini provider selected but GEMINI_API_KEY/GOOGLE_API_KEY is not set"
            )

        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("OpenAI provider selected but OPENAI_API_KEY is not set")

        if self.llm_provider in {"ollama", "vllm"} and not self.local_llm_base_url:
            raise ValueError(
                "Local provider selected but LOCAL_LLM_BASE_URL is not set"
            )
        if not self.session_secret:
            raise ValueError("SESSION_SECRET must not be empty")
        if self.auth_seed_demo_users is None:
            self.auth_seed_demo_users = self.app_env == "dev"
        if self.app_env == "prod" and self.tool_policy_enforcement_mode == "shadow":
            self.tool_policy_enforcement_mode = "enforce"
        if self.app_env in {"staging", "prod"}:
            if self.session_secret == self._DEFAULT_SESSION_SECRET:
                raise ValueError("SESSION_SECRET must be overridden for staging/prod")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be enabled for staging/prod")
            if self.auth_seed_demo_users:
                raise ValueError("AUTH_SEED_DEMO_USERS must be disabled for staging/prod")
        if self.app_env == "prod" and self.app_data_backend == "sqlite":
            raise ValueError("APP_DATA_BACKEND=postgres is required in prod")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be enabled when COOKIE_SAMESITE=none")
        if self.app_data_backend == "postgres" and not self.postgres_dsn:
            raise ValueError("POSTGRES_DSN must be set when APP_DATA_BACKEND=postgres")
        if self.auth_store_backend == "postgres" and not self.postgres_dsn:
            raise ValueError("POSTGRES_DSN must be set when AUTH_STORE_BACKEND=postgres")
        if self.household_store_backend == "postgres" and not self.postgres_dsn:
            raise ValueError("POSTGRES_DSN must be set when HOUSEHOLD_STORE_BACKEND=postgres")
        if self.ephemeral_state_backend == "redis" and not self.redis_url:
            raise ValueError("REDIS_URL must be set when EPHEMERAL_STATE_BACKEND=redis")
        if self.worker_mode == "external" and self.ephemeral_state_backend != "redis":
            raise ValueError("EPHEMERAL_STATE_BACKEND must be redis when WORKER_MODE=external")

        return self

    @property
    def effective_google_api_key(self) -> str | None:
        return self.google_api_key or self.gemini_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings()
