"""Platform tool registry factory.

``build_platform_tool_registry`` assembles the runtime ``ToolRegistry`` with
platform-level tools (currently ``trigger_alert``).  These are use-case–level
tools that coordinate application logic — they are not infrastructure SDKs.
"""

from typing import cast

from pydantic import BaseModel

from dietary_guardian.application.contracts.notifications import AlertRepositoryProtocol
from dietary_guardian.application.notifications.alert_dispatch import trigger_alert
from dietary_guardian.domain.alerts.models import AlertSeverity
from dietary_guardian.infrastructure.tooling.registry import ToolRegistry
from dietary_guardian.domain.tooling.models import (
    ToolPolicyContext,
    ToolSensitivity,
    ToolSideEffect,
    ToolSpec,
)


class TriggerAlertToolInput(BaseModel):
    alert_type: str
    severity: AlertSeverity
    message: str
    destinations: list[str]


class TriggerAlertToolOutput(BaseModel):
    alert_id: str
    correlation_id: str
    deliveries: list[dict[str, str | int | bool | None]]


def build_platform_tool_registry(repository: AlertRepositoryProtocol) -> ToolRegistry:
    """Return a ``ToolRegistry`` pre-loaded with the ``trigger_alert`` platform tool."""
    registry = ToolRegistry()

    def _trigger_alert_tool(payload: BaseModel, _ctx: ToolPolicyContext) -> BaseModel:
        typed = cast(TriggerAlertToolInput, payload)
        alert, deliveries = trigger_alert(
            alert_type=typed.alert_type,
            severity=typed.severity,
            payload={"message": typed.message},
            destinations=typed.destinations,
            repository=repository,
        )
        return TriggerAlertToolOutput(
            alert_id=alert.alert_id,
            correlation_id=alert.correlation_id,
            deliveries=[delivery.model_dump(mode="json") for delivery in deliveries],
        )

    registry.register(
        ToolSpec(
            name="trigger_alert",
            purpose="Queue an alert and drain delivery worker for testing and admin workflows",
            input_schema=TriggerAlertToolInput,
            output_schema=TriggerAlertToolOutput,
            required_scopes=["alert:trigger"],
            side_effect=ToolSideEffect.EXTERNAL,
            sensitivity=ToolSensitivity.NOTIFICATION,
            retryable=False,
            idempotent=False,
        ),
        _trigger_alert_tool,
    )
    return registry


__all__ = ["build_platform_tool_registry", "TriggerAlertToolInput", "TriggerAlertToolOutput"]
