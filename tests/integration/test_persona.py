"""Tests for persona."""

import asyncio

import pytest
from rich.console import Console

from dietary_guardian.agent.dietary.agent import SYSTEM_PROMPT

console = Console()

@pytest.mark.anyio
async def test_uncle_persona():
    console.print("[bold yellow]Vibe Check: Testing 'Uncle Guardian' Persona Logic[/bold yellow]")

    assert "Uncle Guardian" in SYSTEM_PROMPT
    assert "Singlish" in SYSTEM_PROMPT

    console.print(
        "[green]System Prompt successfully updated with 'Uncle' Persona.[/green]"
    )


if __name__ == "__main__":
    asyncio.run(test_uncle_persona())
