"""Observability settings for logging, tracing, and runtime instrumentation."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ObservabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, populate_by_name=True)

    log_level: str = Field(default="INFO", validation_alias="DIETARY_GUARDIAN_LOG_LEVEL")
    readiness_fail_on_warnings: bool | None = None
    api_dev_log_verbose: bool = False
    api_dev_log_headers: bool = False
    api_dev_log_response_headers: bool = False
