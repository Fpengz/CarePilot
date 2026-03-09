"""Outbound channel settings for alerts, messaging, and delivery sinks."""

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    email_from_address: str = "noreply@dietary-guardian.local"
    sms_dev_mode: bool = True
    sms_webhook_url: AnyHttpUrl | str | None = None
    sms_api_key: str | None = None
    sms_sender_id: str = "DietaryGuardian"
