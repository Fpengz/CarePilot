"""
Provide the chat agent.

This agent uses pydantic_ai to generate conversational responses.
"""

from __future__ import annotations

from pydantic_ai import Agent

from dietary_guardian.agent.runtime import LLMFactory
from dietary_guardian.config.llm import LLMCapability

SYSTEM_PROMPT = (
    "You are SEA-LION, a helpful health assistant specialised in Singapore's food, "
    "medications, and chronic-disease management (diabetes, hypertension, cardiovascular). "
    "Answer concisely and accurately. When relevant, reference Singapore-specific "
    "guidelines or food culture."
)


def get_chat_agent() -> Agent[None, str]:
    """Build the pydantic_ai chat agent."""
    model = LLMFactory.get_model(capability=LLMCapability.CHATBOT)
    return Agent(
        model,
        output_type=str,
        system_prompt=SYSTEM_PROMPT,
    )


async def run_chat(
    message: str,
    history: list[dict[str, str]] | None = None,
    system_prompt_override: str | None = None,
) -> str:
    """Run chat against a history of messages."""
    agent = get_chat_agent()
    # pydantic_ai uses messages/history. For now, we'll build a prompt.
    # In a full refactor, we'd pass history to agent.run().
    prompt = message
    if history:
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)
        prompt = f"{history_text}\nuser: {message}"

    result = await agent.run(prompt)
    return result.output
