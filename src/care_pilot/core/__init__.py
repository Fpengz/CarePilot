"""Tiny shared primitives for the feature-first backend."""

from care_pilot.core.errors import ConfigurationError, DomainError
from care_pilot.core.events import DomainEvent
from care_pilot.core.ids import RequestId, UserId, new_id

__all__ = [
    "ConfigurationError",
    "DomainError",
    "DomainEvent",
    "RequestId",
    "UserId",
    "new_id",
]
