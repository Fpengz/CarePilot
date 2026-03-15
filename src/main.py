"""
Provide a CLI-style entrypoint for local dietary analysis.

This module boots configuration, wires the dietary agent runtime, and
executes a sample meal analysis workflow for local testing.
"""

import asyncio

from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from care_pilot.agent.dietary.agent import analyze_dietary_request
from care_pilot.agent.dietary.schemas import DietaryAgentInput
from care_pilot.agent.runtime.llm_factory import LLMFactory
from care_pilot.config.app import AppSettings as Settings, get_settings
from care_pilot.features.profiles.domain.models import (
    MedicalCondition,
    Medication,
    UserProfile,
)
from care_pilot.features.meals.domain.models import (
    Ingredient,
    MealEvent,
    Nutrition,
)
from care_pilot.features.safety.domain.engine import SafetyEngine

console = Console()


def _runtime_summary(settings: Settings) -> str:
    provider = getattr(settings.llm.provider, "value", settings.llm.provider)
    destination = "unavailable"
    try:
        model = LLMFactory.get_model(
            settings=settings, capability=settings.llm.default_capability
        )
        destination = LLMFactory.describe_model_destination(model)
    except Exception:  # noqa: BLE001
        destination = "unavailable"
    return f"Provider: {provider}\nDestination: {destination}"


def bootstrap_runtime_settings() -> Settings:
    try:
        return get_settings()
    except ValidationError as exc:
        console.print("[bold red]Configuration validation failed.[/bold red]")
        console.print(str(exc))
        raise SystemExit(2) from exc


async def main(settings: Settings):
    console.print(
        Panel(_runtime_summary(settings), title="Runtime Configuration")
    )

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
                name="Warfarin",
                dosage="5mg",
                contraindications={"Spinach", "Kale", "Ginkgo"},
            )
        ],
    )

    safety = SafetyEngine(mr_tan)

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

    console.print(
        Panel(
            f"[bold blue]Scenario 1: {mr_tan.name} eating {laksa.name}[/bold blue]"
        )
    )
    warnings = safety.validate_meal(laksa)
    input_data = DietaryAgentInput(
        user_name=mr_tan.name,
        health_goals=[],  # Add health goals if any
        dietary_restrictions=[],  # Add dietary restrictions if any
        meal_name=laksa.name,
        ingredients=[item.name for item in laksa.ingredients],
        portion_size="Standard",
        is_safe=len(warnings) == 0,
        safety_warnings=warnings,
    )
    response = await analyze_dietary_request(input_data)
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
        Panel(
            f"\n[bold red]Scenario 2: {mr_tan.name} eating {spinach_soup.name}[/bold red]"
        )
    )
    warnings = safety.validate_meal(spinach_soup)
    input_data = DietaryAgentInput(
        user_name=mr_tan.name,
        health_goals=[],
        dietary_restrictions=[],
        meal_name=spinach_soup.name,
        ingredients=[item.name for item in spinach_soup.ingredients],
        portion_size="Standard",
        is_safe=len(warnings) == 0,
        safety_warnings=warnings,
    )
    response = await analyze_dietary_request(input_data)
    console.print(response)


if __name__ == "__main__":
    runtime_settings = bootstrap_runtime_settings()
    asyncio.run(main(runtime_settings))
