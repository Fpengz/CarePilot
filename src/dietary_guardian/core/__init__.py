"""Tiny shared primitives for the feature-first backend."""

from dietary_guardian.core.errors import ConfigurationError, DomainError
from dietary_guardian.core.events import DomainEvent
from dietary_guardian.core.ids import RequestId, UserId, new_id

__all__ = [
    "ConfigurationError",
    "DomainError",
    "DomainEvent",
    "RequestId",
    "UserId",
    "new_id",
]
