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
        self._metrics: dict[str, dict[str, float]] = {}

    def register(self, spec: ToolSpec, handler: Any) -> None:
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler
        self._metrics.setdefault(spec.name, {"calls": 0.0, "success": 0.0, "failure": 0.0, "latency_total_ms": 0.0})
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
            result = ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=ToolExecutionError(
                    classification=ToolErrorClass.NOT_FOUND,
                    message="Tool not registered",
                ),
            )
            self._record_metrics(tool_name, result)
            return result
        if spec.allowed_roles and context.role not in spec.allowed_roles:
            result = ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=ToolExecutionError(
                    classification=ToolErrorClass.POLICY_BLOCKED,
                    message=f"Role '{context.role}' cannot execute tool '{tool_name}'",
                ),
                trace_metadata={"role": context.role, "environment": context.environment},
            )
            self._record_metrics(tool_name, result)
            return result
        if spec.allowed_environments and context.environment not in spec.allowed_environments:
            result = ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=ToolExecutionError(
                    classification=ToolErrorClass.POLICY_BLOCKED,
                    message=f"Environment '{context.environment}' blocked for tool '{tool_name}'",
                ),
                trace_metadata={"role": context.role, "environment": context.environment},
            )
            self._record_metrics(tool_name, result)
            return result
        try:
            typed_payload = spec.input_schema.model_validate(payload)
            output = handler(typed_payload, context)
            if not isinstance(output, spec.output_schema):
                output = spec.output_schema.model_validate(output)
            latency_ms = (time.perf_counter() - started) * 1000.0
            result = ToolExecutionResult(
                tool_name=tool_name,
                success=True,
                output=output,
                latency_ms=latency_ms,
                trace_metadata={"role": context.role, "environment": context.environment},
            )
            self._record_metrics(tool_name, result)
            return result
        except ValidationError as exc:
            result = ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=ToolExecutionError(
                    classification=ToolErrorClass.VALIDATION,
                    message="Tool input/output validation failed",
                    details={"errors": exc.errors()},
                ),
                latency_ms=(time.perf_counter() - started) * 1000.0,
            )
            self._record_metrics(tool_name, result)
            return result
        except Exception as exc:  # noqa: BLE001
            logger.exception("tool_registry_execute_failed tool=%s error=%s", tool_name, exc)
            result = ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=ToolExecutionError(
                    classification=ToolErrorClass.INTERNAL,
                    message=str(exc),
                ),
                latency_ms=(time.perf_counter() - started) * 1000.0,
            )
            self._record_metrics(tool_name, result)
            return result

    def _record_metrics(self, tool_name: str, result: ToolExecutionResult) -> None:
        bucket = self._metrics.setdefault(
            tool_name,
            {"calls": 0.0, "success": 0.0, "failure": 0.0, "latency_total_ms": 0.0},
        )
        bucket["calls"] += 1
        bucket["latency_total_ms"] += max(0.0, result.latency_ms)
        if result.success:
            bucket["success"] += 1
        else:
            bucket["failure"] += 1

    def snapshot_metrics(self) -> dict[str, dict[str, float]]:
        snapshot: dict[str, dict[str, float]] = {}
        for name, bucket in self._metrics.items():
            calls = bucket["calls"]
            snapshot[name] = {
                "calls": calls,
                "success": bucket["success"],
                "failure": bucket["failure"],
                "avg_latency_ms": (bucket["latency_total_ms"] / calls) if calls > 0 else 0.0,
            }
        return snapshot
