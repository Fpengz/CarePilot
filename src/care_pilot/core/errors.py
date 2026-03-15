"""
Define domain-neutral error primitives.

This module provides lightweight error types shared across the system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class DomainError(Exception):
    """Base error for deterministic application failures."""


class ConfigurationError(DomainError):
    """Raised when runtime configuration is invalid."""


@dataclass(slots=True)
class ApiAppError(Exception):
    status_code: int
    code: str
    message: str
    details: dict[str, object] = field(default_factory=dict)
    headers: dict[str, str] | None = None


def build_api_error(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> ApiAppError:
    return ApiAppError(
        status_code=status_code,
        code=code,
        message=message,
        details={str(k): v for k, v in (details or {}).items()},
    )
