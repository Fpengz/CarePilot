"""Domain-neutral error primitives."""


class DomainError(Exception):
    """Base error for deterministic application failures."""


class ConfigurationError(DomainError):
    """Raised when runtime configuration is invalid."""
