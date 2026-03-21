"""
Provide the multi-agent compatible medication perception agent.

This agent extracts structured medication regimens from prescriptions or text instructions.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic_ai import Agent

from care_pilot.agent.core.contracts import (
    AgentRecommendation,
    AgentRequest,
    AgentResponse,
)
from care_pilot.agent.runtime.llm_factory import LLMFactory
from care_pilot.config.llm import LLMCapability
from care_pilot.features.medications.intake.models import MedicationParseOutput

SYSTEM_PROMPT = (
    "You are the 'Prescription Parser' Specialist node. "
    "Your role is to extract structured medication instructions from input text or images. "
    "\n\nReturn strict JSON matching the MedicationParseOutput schema. "
    "\nExtract: medication name, dosage, frequency, timing (pre/post meal), and start/end dates. "
    "\n\nIf timing is ambiguous, flag it in the 'warnings' field."
)


def get_medication_agent() -> Agent[None, MedicationParseOutput]:
    """Build the pydantic_ai agent instance."""
    model = LLMFactory.get_model(capability=LLMCapability.CHATBOT) # Use general purpose for now
    return cast(
        Any,
        Agent(
            model,
            output_type=MedicationParseOutput,
            system_prompt=SYSTEM_PROMPT,
        ),
    )


async def run_medication_agent(request: AgentRequest) -> AgentResponse:
    """Execute the medication specialist agent."""
    agent = get_medication_agent()

    text_input = request.inputs.get("text_context") or request.goal

    result = await agent.run(text_input)
    parsed = result.output

    recommendations = []
    if parsed.confidence_score < 0.8:
        recommendations.append(
            AgentRecommendation(
                title="Verify Instructions",
                summary="The parser is not fully confident in these instructions. Please verify against your actual prescription.",
                priority="high"
            )
        )

    for warning in parsed.warnings:
        recommendations.append(
            AgentRecommendation(
                title="Ambiguous Instruction",
                summary=warning,
                priority="medium"
            )
        )

    return AgentResponse(
        agent_name="medication_agent",
        status="success" if parsed.instructions else "blocked",
        summary=f"Extracted {len(parsed.instructions)} medication instructions.",
        structured_output=parsed.model_dump(),
        recommendations=recommendations,
        confidence=parsed.confidence_score,
        reasoning_trace=["Parsed prescription text", "Normalized timing and dosage"]
    )
