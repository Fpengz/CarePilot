"""Context ingestion helpers for the meal pipeline."""

from __future__ import annotations

from datetime import UTC, datetime

from care_pilot.features.meals.domain.models import ContextSnapshot


def build_context_snapshot(
    *,
    session: dict[str, object],
    request_id: str | None,
    correlation_id: str | None,
    user_agent: str | None,
    client_ip: str | None,
) -> ContextSnapshot:
    return ContextSnapshot(
        timestamp=datetime.now(UTC),
        request_id=request_id,
        correlation_id=correlation_id,
        user_agent=user_agent,
        client_ip=client_ip,
        user_context_snapshot={
            "profile_mode": str(session.get("profile_mode", "")),
            "display_name": str(session.get("display_name", "")),
        },
    )


__all__ = ["build_context_snapshot"]
