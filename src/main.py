"""Module for main."""

import asyncio

from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from dietary_guardian.capabilities.dietary import process_meal_request
from dietary_guardian.config.app import AppSettings as Settings, get_settings
from dietary_guardian.domain.identity.models import (
    MedicalCondition,
    Medication,
    UserProfile,
)
from dietary_guardian.infrastructure.llm import LLMFactory
from dietary_guardian.domain.meals.models import Ingredient, MealEvent, Nutrition

console = Console()


def bootstrap_runtime_settings() -> Settings:
    try:
        return get_settings()
    except ValidationError as exc:
        console.print("[bold red]Configuration validation failed.[/bold red]")
        console.print(str(exc))
        raise SystemExit(2) from exc


def _runtime_summary(settings: Settings) -> str:
    model = LLMFactory.get_model()
    return (
        f"Provider: {settings.llm.provider}\n"
        f"Model: {getattr(model, 'model_name', 'unknown')}\n"
        f"Destination: {LLMFactory.describe_model_destination(model)}"
    )


async def main(settings: Settings):
    console.print(Panel(_runtime_summary(settings), title="Runtime Configuration"))

    # Setup Mr. Tan
    mr_tan = UserProfile(
        id="user_001",
        name="Mr. Tan",
        age=68,
        conditions=[
            MedicalCondition(name="Type 2 Diabetes", severity="High"),
            MedicalCondition(name="Hypertension", severity="Medium"),
        ],
        medications=[
            Medication(
                name="Warfarin", dosage="5mg", contraindications={"Spinach", "Kale", "Ginkgo"}
            )
        ],
    )

    # Scenario 1: High Sodium Laksa
    laksa = MealEvent(
        name="Laksa",
        ingredients=[
            Ingredient(name="Rice Noodles"),
            Ingredient(name="Coconut Milk Gravy"),
            Ingredient(name="Fish Cake"),
            Ingredient(name="Cockles"),
        ],
        nutrition=Nutrition(
            calories=600,
            carbs_g=70,
            sugar_g=5,
            protein_g=20,
            fat_g=30,
            sodium_mg=1500,  # High sodium
        ),
    )

    console.print(Panel(f"[bold blue]Scenario 1: {mr_tan.name} eating {laksa.name}[/bold blue]"))
    response = await process_meal_request(mr_tan, laksa)
    console.print(response)

    # Scenario 2: Safety Violation (Warfarin + Spinach)
    spinach_soup = MealEvent(
        name="Spinach & Egg Soup",
        ingredients=[
            Ingredient(name="Spinach"),
            Ingredient(name="Egg"),
            Ingredient(name="Anchovy Broth"),
        ],
        nutrition=Nutrition(
            calories=150,
            carbs_g=5,
            sugar_g=1,
            protein_g=10,
            fat_g=5,
            sodium_mg=400,
        ),
    )

    console.print(
        Panel(f"\n[bold red]Scenario 2: {mr_tan.name} eating {spinach_soup.name}[/bold red]")
    )
    response = await process_meal_request(mr_tan, spinach_soup)
    console.print(response)


if __name__ == "__main__":
    runtime_settings = bootstrap_runtime_settings()
    asyncio.run(main(runtime_settings))
