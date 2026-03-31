"""
Expose merged runtime configuration.

This module aggregates settings from config submodules into a single
runtime configuration surface.
"""

from typing import Literal

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# API settings (from config/api.py)
# ---------------------------------------------------------------------------


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="API_",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    host: str = "127.0.0.1"
    port: int = Field(default=8001, ge=1, le=65535)
    cors_origins: str = "http://localhost:3000"
    cors_methods: str = "GET,POST,PATCH,DELETE,OPTIONS"
    cors_headers: str = "Content-Type,X-Requested-With,Authorization"
    meal_upload_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=50 * 1024 * 1024)
    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    rate_limit_auth_login_max_requests: int = Field(default=20, ge=1, le=500)
    rate_limit_meal_analyze_max_requests: int = Field(default=20, ge=1, le=500)
    rate_limit_recommendations_generate_max_requests: int = Field(default=10, ge=1, le=500)


# ---------------------------------------------------------------------------
# Auth settings (from config/auth.py)
# ---------------------------------------------------------------------------


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, populate_by_name=True)

    session_secret: str = Field(
        default="dev-insecure-session-secret-change-me",
        validation_alias="SESSION_SECRET",
    )
    cookie_secure: bool = Field(default=False, validation_alias="COOKIE_SECURE")
    cookie_samesite: Literal["lax", "strict", "none"] = Field(
        default="lax", validation_alias="COOKIE_SAMESITE"
    )
    password_hash_scheme: str = Field(
        default="pbkdf2_sha256", validation_alias="AUTH_PASSWORD_HASH_SCHEME"
    )
    store_backend: Literal["in_memory", "sqlite"] = Field(
        default="sqlite", validation_alias="AUTH_STORE_BACKEND"
    )
    sqlite_db_path: str = Field(
        default="data/care_pilot_auth.db",
        validation_alias="AUTH_SQLITE_DB_PATH",
    )
    session_ttl_seconds: int = Field(
        default=86400,
        ge=1,
        le=60 * 60 * 24 * 30,
        validation_alias="AUTH_SESSION_TTL_SECONDS",
    )
    login_max_failed_attempts: int = Field(
        default=5,
        ge=1,
        le=20,
        validation_alias="AUTH_LOGIN_MAX_FAILED_ATTEMPTS",
    )
    login_failure_window_seconds: int = Field(
        default=300,
        ge=1,
        le=3600,
        validation_alias="AUTH_LOGIN_FAILURE_WINDOW_SECONDS",
    )
    login_lockout_seconds: int = Field(
        default=300,
        ge=1,
        le=86400,
        validation_alias="AUTH_LOGIN_LOCKOUT_SECONDS",
    )
    audit_events_max_entries: int = Field(
        default=500,
        ge=10,
        le=10000,
        validation_alias="AUTH_AUDIT_EVENTS_MAX_ENTRIES",
    )
    seed_demo_users: bool = Field(default=True, validation_alias="AUTH_SEED_DEMO_USERS")
    demo_member_password: str = Field(default="member-pass", validation_alias="AUTH_DEMO_MEMBER_PASSWORD")
    demo_helper_password: str = Field(default="helper-pass", validation_alias="AUTH_DEMO_HELPER_PASSWORD")
    demo_admin_password: str = Field(default="admin-pass", validation_alias="AUTH_DEMO_ADMIN_PASSWORD")


# ---------------------------------------------------------------------------
# Channel settings (from config/channels.py)
# ---------------------------------------------------------------------------


class ChannelSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, populate_by_name=True)

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
    email_from_address: str = "noreply@care-pilot.local"
    sms_dev_mode: bool = True
    sms_webhook_url: AnyHttpUrl | str | None = None
    sms_api_key: str | None = None
    sms_sender_id: str = "CarePilot"


# ---------------------------------------------------------------------------
# Storage settings (from config/storage.py)
# ---------------------------------------------------------------------------


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, populate_by_name=True)

    app_data_backend: Literal["sqlite", "postgresql"] = "sqlite"
    api_sqlite_db_path: str = "data/care_pilot_api.db"
    api_postgres_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    household_store_backend: Literal["sqlite", "postgresql"] = "sqlite"
    ephemeral_state_backend: Literal["in_memory", "redis"] = "in_memory"
    redis_url: str | None = None
    redis_namespace: str = "care_pilot"
    redis_default_ttl_seconds: int = Field(default=300, ge=1, le=86400)
    redis_lock_ttl_seconds: int = Field(default=30, ge=1, le=3600)
    redis_worker_signal_channel: str = "workers.ready"


# ---------------------------------------------------------------------------
# Worker settings (from config/workers.py)
# ---------------------------------------------------------------------------


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WORKER_",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    worker_mode: Literal["in_process", "external"] = "in_process"
    reminder_scheduler_interval_seconds: int = Field(default=30, ge=5, le=3600)
    reminder_scheduler_batch_size: int = Field(default=100, ge=1, le=1000)
    reminder_max_late_minutes: int = Field(default=60, ge=0, le=1440)
    reminder_worker_poll_interval_seconds: int = Field(default=15, ge=1, le=3600)
    outbox_worker_poll_interval_seconds: int = Field(default=5, ge=1, le=3600)
    workflow_trace_persistence_enabled: bool = False
    workflow_contract_bootstrap: bool = True
    tool_policy_enforcement_mode: Literal["shadow", "enforce"] = "shadow"
    use_alert_outbox_v2: bool = True
    alert_worker_max_attempts: int = 3
    alert_worker_concurrency: int = 4


class FeatureFlags(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FEATURE_",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    enable_fast_path_intent: bool = True
    enable_context_pruning: bool = True
    enable_multi_modal_ingestion: bool = False
    enable_proactive_nudge: bool = False
    enable_debug_tools: bool = False


# ---------------------------------------------------------------------------
# Chat settings (from config/chat.py)
# ---------------------------------------------------------------------------


class ChatSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    api_key: str | None = Field(default=None, validation_alias="SEALION_API")
    base_url: str = Field(
        default="https://api.sea-lion.ai/v1",
        validation_alias="SEALION_BASE_URL",
    )
    model_cache_dir: str | None = Field(default=None, validation_alias="CHAT_MODEL_CACHE_DIR")
    model_id: str = Field(
        default="aisingapore/Gemma-SEA-LION-v4-27B-IT",
        validation_alias="CHAT_MODEL_ID",
    )
    reasoning_model_id: str = Field(
        default="aisingapore/Llama-SEA-LION-v3.5-70B-R",
        validation_alias="REASONING_MODEL_ID",
    )
    stream_max_retries: int = Field(
        default=2, ge=0, le=5, validation_alias="CHAT_STREAM_MAX_RETRIES"
    )
    stream_backoff_seconds: float = Field(
        default=0.5,
        ge=0.0,
        le=10.0,
        validation_alias="CHAT_STREAM_BACKOFF_SECONDS",
    )


# ---------------------------------------------------------------------------
# Emotion settings (from config/emotion.py)
# ---------------------------------------------------------------------------


class EmotionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EMOTION_",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    inference_enabled: bool = False
    speech_enabled: bool = False
    runtime_mode: Literal["in_process", "remote"] = "in_process"
    remote_base_url: str = "http://localhost:8002"
    request_timeout_seconds: float = Field(default=15.0, ge=0.1, le=300.0)
    model_device: Literal["auto", "cpu", "cuda"] = "auto"
    model_cache_dir: str | None = Field(default=None, validation_alias="EMOTION_MODEL_CACHE_DIR")
    text_model_id: str = "j-hartmann/emotion-english-distilroberta-base"
    speech_model_id: str = "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition"
    fusion_model_id: str | None = None
    asr_model_id: str = "openai/whisper-tiny"
    history_window: int = Field(default=5, ge=1, le=20)
    source_commit: str = "9afc3f1a3a3fec71a4e5920d8f4103710b337ecc"


# ---------------------------------------------------------------------------
# Observability settings (from config/observability.py)
# ---------------------------------------------------------------------------


class ObservabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, populate_by_name=True)

    log_level: str = Field(default="INFO", validation_alias="CARE_PILOT_LOG_LEVEL")
    log_llm_payloads: bool = Field(default=False, validation_alias="CARE_PILOT_LOG_LLM_PAYLOADS")
    log_hf_payloads: bool = Field(default=False, validation_alias="CARE_PILOT_LOG_HF_PAYLOADS")
    readiness_fail_on_warnings: bool | None = None
    api_dev_log_verbose: bool = False
    api_dev_log_headers: bool = False
    api_dev_log_response_headers: bool = False
    logfire_token: str | None = Field(default=None, validation_alias="LOGFIRE_TOKEN")
    logfire_enabled: bool = Field(default=False, validation_alias="LOGFIRE_ENABLED")


# ---------------------------------------------------------------------------
# Memory settings (Mem0)
# ---------------------------------------------------------------------------


class MemorySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEM0_",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    enabled: bool | None = None
    api_key: str | None = None
    base_url: str | None = None
    top_k: int = Field(default=5, ge=1, le=25)

    @model_validator(mode="after")
    def _default_enabled(self) -> "MemorySettings":
        if self.enabled is None:
            self.enabled = bool(self.api_key)
        return self
