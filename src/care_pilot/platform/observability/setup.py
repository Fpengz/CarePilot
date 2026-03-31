"""
Unified observability setup for the CarePilot runtime.
"""

from __future__ import annotations

import logfire
from care_pilot.config.app import get_settings


def setup_observability() -> None:
    """Initialize logfire and instrument all supported libraries."""
    settings = get_settings()

    if not settings.observability.logfire_enabled:
        return

    # Configure logfire
    logfire.configure(
        token=settings.observability.logfire_token,
        environment=settings.app.env,
        service_name="care-pilot-api",
    )

    # Instrument infrastructure libraries
    if hasattr(logfire, "instrument_httpx"):
        logfire.instrument_httpx()  # type: ignore

    if hasattr(logfire, "instrument_pydantic"):
        logfire.instrument_pydantic()  # type: ignore

    # logfire.instrument_sqlalchemy() will be called once we have the engine
    # logfire.instrument_fastapi() will be called in the API entry point
