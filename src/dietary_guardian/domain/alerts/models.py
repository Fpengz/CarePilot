"""Domain model definitions for the alerts subdomain: alert messages and outbox records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

AlertSeverity = Literal["info", "warning", "critical"]
OutboxState = Literal["pending", "processing", "delivered", "dead_letter"]


class AlertMessage(BaseModel):
    alert_id: str
    type: str
    severity: AlertSeverity
    payload: dict[str, str]
    destinations: list[str]
    correlation_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OutboxRecord(BaseModel):
    alert_id: str
    sink: str
    type: str
    severity: AlertSeverity
    payload: dict[str, str]
    correlation_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    state: OutboxState = "pending"
    attempt_count: int = 0
    next_attempt_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_error: str | None = None
    lease_owner: str | None = None
    lease_until: datetime | None = None
    idempotency_key: str


class AlertDeliveryResult(BaseModel):
    alert_id: str
    sink: str
    success: bool
    attempt: int
    destination: str | None = None
    provider_reference: str | None = None
    error: str | None = None
