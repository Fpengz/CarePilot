"""Tests for persona."""

import asyncio

import pytest
from rich.console import Console

from dietary_guardian.capabilities.dietary import dietary_agent

console = Console()

@pytest.mark.anyio
async def test_uncle_persona():
    console.print("[bold yellow]Vibe Check: Testing 'Uncle Guardian' Persona Logic[/bold yellow]")


    # Verify the system prompt is set correctly on the agent
    # In pydantic-ai, system prompts are stored in _system_prompts
    prompt_found = any("Uncle Guardian" in p for p in dietary_agent._system_prompts)
    assert prompt_found
    assert any("Singlish" in p for p in dietary_agent._system_prompts)

    console.print(
        "[green]System Prompt successfully updated with 'Uncle' Persona.[/green]"
    )


if __name__ == "__main__":
    asyncio.run(test_uncle_persona())
