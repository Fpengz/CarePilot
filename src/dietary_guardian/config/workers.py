"""Worker execution and queue-coordination settings for background jobs."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, populate_by_name=True)

    worker_mode: Literal["in_process", "external"] = "in_process"
    reminder_scheduler_interval_seconds: int = Field(default=30, ge=5, le=3600)
    reminder_scheduler_batch_size: int = Field(default=100, ge=1, le=1000)
    reminder_worker_poll_interval_seconds: int = Field(default=15, ge=1, le=3600)
    outbox_worker_poll_interval_seconds: int = Field(default=5, ge=1, le=3600)
    workflow_trace_persistence_enabled: bool = False
    workflow_contract_bootstrap: bool = True
    tool_policy_enforcement_mode: Literal["shadow", "enforce"] = "shadow"
    use_alert_outbox_v2: bool = True
    alert_worker_max_attempts: int = 3
    alert_worker_concurrency: int = 4
