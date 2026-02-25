from typing import cast

from pydantic import BaseModel

from dietary_guardian.models.alerting import AlertSeverity
from dietary_guardian.models.tooling import ToolPolicyContext, ToolSensitivity, ToolSideEffect, ToolSpec
from dietary_guardian.services.notification_service import trigger_alert
from dietary_guardian.services.repository import SQLiteRepository
from dietary_guardian.services.tool_registry import ToolRegistry


class TriggerAlertToolInput(BaseModel):
    alert_type: str
    severity: AlertSeverity
    message: str
    destinations: list[str]


class TriggerAlertToolOutput(BaseModel):
    alert_id: str
    correlation_id: str
    deliveries: list[dict[str, str | int | bool | None]]


def build_platform_tool_registry(repository: SQLiteRepository) -> ToolRegistry:
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
            purpose="Queue an alert and drain delivery worker for testing and operator workflows",
            input_schema=TriggerAlertToolInput,
            output_schema=TriggerAlertToolOutput,
            # The Streamlit dev panel exposes patient/caregiver/clinician roles.
            allowed_roles=["patient", "caregiver", "clinician"],
            side_effect=ToolSideEffect.EXTERNAL,
            sensitivity=ToolSensitivity.NOTIFICATION,
            retryable=False,
            idempotent=False,
        ),
        _trigger_alert_tool,
    )
    return registry
