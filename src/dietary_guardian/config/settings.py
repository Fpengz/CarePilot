from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, model_validator
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

    dietary_guardian_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_dev_mode: bool = True

    use_inference_engine_v2: bool = True
    use_alert_outbox_v2: bool = True
    alert_worker_max_attempts: int = 3
    alert_worker_concurrency: int = 4

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

        return self

    @property
    def effective_google_api_key(self) -> str | None:
        return self.google_api_key or self.gemini_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings()
