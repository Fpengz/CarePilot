from pydantic import BaseModel

from dietary_guardian.models.tooling import (
    ToolErrorClass,
    ToolPolicyContext,
    ToolSensitivity,
    ToolSideEffect,
    ToolSpec,
)
from dietary_guardian.infrastructure.tooling.registry import ToolRegistry


class EchoInput(BaseModel):
    text: str


class EchoOutput(BaseModel):
    echoed: str


def test_tool_registry_blocks_missing_scope() -> None:
    registry = ToolRegistry()
    def handler(payload: BaseModel, _ctx: ToolPolicyContext) -> BaseModel:
        typed = EchoInput.model_validate(payload)
        return EchoOutput(echoed=typed.text)

    registry.register(
        ToolSpec(
            name="echo_caregiver",
            purpose="Echo for caregiver workflows",
            input_schema=EchoInput,
            output_schema=EchoOutput,
            required_scopes=["debug:echo"],
            side_effect=ToolSideEffect.READ,
            sensitivity=ToolSensitivity.LOW,
        ),
        handler,
    )

    result = registry.execute(
        "echo_caregiver",
        {"text": "hello"},
        ToolPolicyContext(account_role="member", scopes=[], environment="dev"),
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.classification == ToolErrorClass.POLICY_BLOCKED


def test_tool_registry_executes_and_returns_typed_output() -> None:
    registry = ToolRegistry()
    def handler(payload: BaseModel, _ctx: ToolPolicyContext) -> BaseModel:
        typed = EchoInput.model_validate(payload)
        return EchoOutput(echoed=typed.text.upper())

    registry.register(
        ToolSpec(
            name="echo_patient",
            purpose="Echo for patient workflows",
            input_schema=EchoInput,
            output_schema=EchoOutput,
            required_scopes=["echo:read"],
            side_effect=ToolSideEffect.READ,
            sensitivity=ToolSensitivity.LOW,
        ),
        handler,
    )

    result = registry.execute(
        "echo_patient",
        {"text": "hello"},
        ToolPolicyContext(account_role="member", scopes=["echo:read"], environment="dev"),
    )

    assert result.success is True
    output = EchoOutput.model_validate(result.output)
    assert output.echoed == "HELLO"
