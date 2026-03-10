"""Tests for tool registry metrics."""

from pydantic import BaseModel

from dietary_guardian.models.tooling import (
    ToolPolicyContext,
    ToolSensitivity,
    ToolSideEffect,
    ToolSpec,
)
from dietary_guardian.infrastructure.tooling.registry import ToolRegistry


class PingInput(BaseModel):
    value: str


class PingOutput(BaseModel):
    pong: str


def test_tool_registry_metrics_track_success_and_failure() -> None:
    registry = ToolRegistry()

    def ok_handler(payload: BaseModel, _ctx: ToolPolicyContext) -> BaseModel:
        typed = PingInput.model_validate(payload)
        return PingOutput(pong=typed.value)

    registry.register(
        ToolSpec(
            name="ping",
            purpose="test ping",
            input_schema=PingInput,
            output_schema=PingOutput,
            required_scopes=["ping:run"],
            side_effect=ToolSideEffect.READ,
            sensitivity=ToolSensitivity.LOW,
        ),
        ok_handler,
    )

    ok = registry.execute("ping", {"value": "ok"}, ToolPolicyContext(account_role="member", scopes=["ping:run"]))
    blocked = registry.execute("ping", {"value": "x"}, ToolPolicyContext(account_role="member", scopes=[]))

    assert ok.success is True
    assert blocked.success is False

    metrics = registry.snapshot_metrics()
    assert metrics["ping"]["calls"] == 2
    assert metrics["ping"]["success"] == 1
    assert metrics["ping"]["failure"] == 1
    assert metrics["ping"]["avg_latency_ms"] >= 0
