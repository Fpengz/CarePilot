"""Compatibility re-export: definitions have moved to dietary_guardian.domain.alerts.models."""
# ruff: noqa: F401
from dietary_guardian.domain.alerts.models import (
    AlertDeliveryResult,
    AlertMessage,
    AlertSeverity,
    OutboxRecord,
    OutboxState,
)
