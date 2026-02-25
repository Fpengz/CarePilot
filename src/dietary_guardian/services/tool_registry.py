import time
from typing import Any

from pydantic import ValidationError

from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.tooling import (
    ToolErrorClass,
    ToolExecutionError,
    ToolExecutionResult,
    ToolPolicyContext,
    ToolSpec,
)

logger = get_logger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, Any] = {}

    def register(self, spec: ToolSpec, handler: Any) -> None:
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler
        logger.info(
            "tool_registry_register tool=%s side_effect=%s sensitivity=%s roles=%s",
            spec.name,
            spec.side_effect,
            spec.sensitivity,
            spec.allowed_roles,
        )

    def list_specs(self) -> list[ToolSpec]:
        return list(self._specs.values())

    def execute(
        self,
        tool_name: str,
        payload: dict[str, object],
        context: ToolPolicyContext,
    ) -> ToolExecutionResult:
        started = time.perf_counter()
        spec = self._specs.get(tool_name)
        handler = self._handlers.get(tool_name)
        if spec is None or handler is None:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=ToolExecutionError(
                    classification=ToolErrorClass.NOT_FOUND,
                    message="Tool not registered",
                ),
            )
        if spec.allowed_roles and context.role not in spec.allowed_roles:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=ToolExecutionError(
                    classification=ToolErrorClass.POLICY_BLOCKED,
                    message=f"Role '{context.role}' cannot execute tool '{tool_name}'",
                ),
                trace_metadata={"role": context.role, "environment": context.environment},
            )
        if spec.allowed_environments and context.environment not in spec.allowed_environments:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=ToolExecutionError(
                    classification=ToolErrorClass.POLICY_BLOCKED,
                    message=f"Environment '{context.environment}' blocked for tool '{tool_name}'",
                ),
                trace_metadata={"role": context.role, "environment": context.environment},
            )
        try:
            typed_payload = spec.input_schema.model_validate(payload)
            output = handler(typed_payload, context)
            if not isinstance(output, spec.output_schema):
                output = spec.output_schema.model_validate(output)
            latency_ms = (time.perf_counter() - started) * 1000.0
            return ToolExecutionResult(
                tool_name=tool_name,
                success=True,
                output=output,
                latency_ms=latency_ms,
                trace_metadata={"role": context.role, "environment": context.environment},
            )
        except ValidationError as exc:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=ToolExecutionError(
                    classification=ToolErrorClass.VALIDATION,
                    message="Tool input/output validation failed",
                    details={"errors": exc.errors()},
                ),
                latency_ms=(time.perf_counter() - started) * 1000.0,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("tool_registry_execute_failed tool=%s error=%s", tool_name, exc)
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=ToolExecutionError(
                    classification=ToolErrorClass.INTERNAL,
                    message=str(exc),
                ),
                latency_ms=(time.perf_counter() - started) * 1000.0,
            )
