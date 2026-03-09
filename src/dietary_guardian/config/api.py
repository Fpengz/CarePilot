"""HTTP API settings for transport-level request and session behavior."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="API_", extra="ignore", case_sensitive=False, populate_by_name=True)

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
