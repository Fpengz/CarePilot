from pydantic import BaseModel

from dietary_guardian.models.tooling import (
    ToolErrorClass,
    ToolPolicyContext,
    ToolSensitivity,
    ToolSideEffect,
    ToolSpec,
)
from dietary_guardian.services.tool_registry import ToolRegistry


class EchoInput(BaseModel):
    text: str


class EchoOutput(BaseModel):
    echoed: str


def test_tool_registry_blocks_disallowed_role() -> None:
    registry = ToolRegistry()
    def handler(payload: BaseModel, _ctx: ToolPolicyContext) -> BaseModel:
        typed = EchoInput.model_validate(payload)
        return EchoOutput(echoed=typed.text)

    registry.register(
        ToolSpec(
            name="echo_operator",
            purpose="Echo for operator workflows",
            input_schema=EchoInput,
            output_schema=EchoOutput,
            allowed_roles=["operator"],
            side_effect=ToolSideEffect.READ,
            sensitivity=ToolSensitivity.LOW,
        ),
        handler,
    )

    result = registry.execute(
        "echo_operator",
        {"text": "hello"},
        ToolPolicyContext(role="patient", environment="dev"),
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
            allowed_roles=["patient", "clinician"],
            side_effect=ToolSideEffect.READ,
            sensitivity=ToolSensitivity.LOW,
        ),
        handler,
    )

    result = registry.execute(
        "echo_patient",
        {"text": "hello"},
        ToolPolicyContext(role="patient", environment="dev"),
    )

    assert result.success is True
    output = EchoOutput.model_validate(result.output)
    assert output.echoed == "HELLO"
