"""Meal catalog seed data and query helpers.

``DEFAULT_MEAL_CATALOG`` is the built-in reference catalog of Singapore hawker
items used for recommendation seeding and food matching.  Helper functions
provide normalised-text lookup over the catalog.
"""

from __future__ import annotations

from dietary_guardian.domain.recommendations.models import MealCatalogItem
from dietary_guardian.domain.meals.models import Nutrition

DEFAULT_MEAL_CATALOG: tuple[MealCatalogItem, ...] = (
    MealCatalogItem(
        meal_id="sg.breakfast.soft_boiled_eggs_wholemeal_toast",
        title="Soft-boiled eggs with wholemeal toast",
        slot="breakfast",
        venue_type="kopitiam breakfast set",
        cuisine_tags=["local"],
        ingredient_tags=["eggs", "wholemeal bread"],
        preparation_tags=["boiled", "toast"],
        nutrition=Nutrition(calories=280, carbs_g=28, sugar_g=3, protein_g=14, fat_g=11, sodium_mg=340, fiber_g=4),
        price_tier="budget",
        health_tags=["lower_sugar", "heart_health", "higher_protein"],
    ),
    MealCatalogItem(
        meal_id="sg.breakfast.plain_thosai_dhal",
        title="Plain thosai with dhal",
        slot="breakfast",
        venue_type="hawker breakfast",
        cuisine_tags=["indian"],
        ingredient_tags=["lentils", "rice", "spices"],
        preparation_tags=["griddled"],
        nutrition=Nutrition(calories=320, carbs_g=48, sugar_g=4, protein_g=9, fat_g=8, sodium_mg=380, fiber_g=5),
        price_tier="budget",
        health_tags=["heart_health", "lower_sugar", "higher_fiber"],
    ),
    MealCatalogItem(
        meal_id="sg.breakfast.kaya_toast_set",
        title="Kaya toast set",
        slot="breakfast",
        venue_type="kopitiam breakfast set",
        cuisine_tags=["local"],
        ingredient_tags=["toast", "kaya", "eggs"],
        preparation_tags=["toast"],
        nutrition=Nutrition(calories=420, carbs_g=52, sugar_g=18, protein_g=10, fat_g=16, sodium_mg=420, fiber_g=2),
        price_tier="budget",
        health_tags=["comfort"],
    ),
    MealCatalogItem(
        meal_id="sg.lunch.sliced_fish_soup_rice",
        title="Sliced fish soup with rice",
        slot="lunch",
        venue_type="hawker stall",
        cuisine_tags=["teochew", "local"],
        ingredient_tags=["fish", "vegetables", "rice"],
        preparation_tags=["soup"],
        nutrition=Nutrition(calories=430, carbs_g=46, sugar_g=2, protein_g=27, fat_g=11, sodium_mg=620, fiber_g=3),
        price_tier="moderate",
        health_tags=["lower_sodium", "heart_health", "higher_protein"],
    ),
    MealCatalogItem(
        meal_id="sg.lunch.thunder_tea_rice",
        title="Thunder tea rice",
        slot="lunch",
        venue_type="food court",
        cuisine_tags=["hakka", "local"],
        ingredient_tags=["greens", "tofu", "brown rice"],
        preparation_tags=["mixed bowl"],
        nutrition=Nutrition(calories=470, carbs_g=49, sugar_g=3, protein_g=18, fat_g=17, sodium_mg=520, fiber_g=7),
        price_tier="moderate",
        health_tags=["heart_health", "lower_sugar", "higher_fiber"],
    ),
    MealCatalogItem(
        meal_id="sg.lunch.mee_rebus",
        title="Mee rebus",
        slot="lunch",
        venue_type="hawker stall",
        cuisine_tags=["malay", "local"],
        ingredient_tags=["noodles", "gravy", "egg"],
        preparation_tags=["noodles"],
        nutrition=Nutrition(calories=680, carbs_g=82, sugar_g=14, protein_g=18, fat_g=24, sodium_mg=1460, fiber_g=4),
        price_tier="budget",
        health_tags=["comfort"],
    ),
    MealCatalogItem(
        meal_id="sg.lunch.laksa",
        title="Laksa",
        slot="lunch",
        venue_type="hawker stall",
        cuisine_tags=["peranakan", "local"],
        ingredient_tags=["noodles", "coconut", "shellfish"],
        preparation_tags=["noodles", "soup"],
        nutrition=Nutrition(calories=690, carbs_g=62, sugar_g=7, protein_g=21, fat_g=34, sodium_mg=1650, fiber_g=3),
        price_tier="moderate",
        health_tags=["comfort"],
    ),
    MealCatalogItem(
        meal_id="sg.dinner.yong_tau_foo_clear_soup",
        title="Yong tau foo clear soup with tofu and greens",
        slot="dinner",
        venue_type="hawker stall",
        cuisine_tags=["hakka", "local"],
        ingredient_tags=["tofu", "greens", "fish paste"],
        preparation_tags=["soup"],
        nutrition=Nutrition(calories=440, carbs_g=34, sugar_g=4, protein_g=26, fat_g=17, sodium_mg=740, fiber_g=5),
        price_tier="moderate",
        health_tags=["lower_sodium", "heart_health", "lower_sugar"],
    ),
    MealCatalogItem(
        meal_id="sg.dinner.steamed_chicken_rice",
        title="Steamed chicken rice with extra cucumber",
        slot="dinner",
        venue_type="hawker stall",
        cuisine_tags=["hainanese", "local"],
        ingredient_tags=["chicken", "rice", "cucumber"],
        preparation_tags=["steamed"],
        nutrition=Nutrition(calories=560, carbs_g=58, sugar_g=3, protein_g=26, fat_g=20, sodium_mg=980, fiber_g=2),
        price_tier="moderate",
        health_tags=["higher_protein"],
    ),
    MealCatalogItem(
        meal_id="sg.dinner.char_kway_teow",
        title="Char kway teow",
        slot="dinner",
        venue_type="hawker stall",
        cuisine_tags=["hokkien", "local"],
        ingredient_tags=["noodles", "soy sauce", "lard"],
        preparation_tags=["stir_fry"],
        nutrition=Nutrition(calories=760, carbs_g=71, sugar_g=9, protein_g=22, fat_g=39, sodium_mg=1780, fiber_g=2),
        price_tier="budget",
        health_tags=["comfort"],
    ),
    MealCatalogItem(
        meal_id="sg.snack.unsweetened_soy_nuts",
        title="Unsweetened soy milk with nuts",
        slot="snack",
        venue_type="grab-and-go",
        cuisine_tags=["local"],
        ingredient_tags=["soy", "nuts"],
        preparation_tags=["cold"],
        nutrition=Nutrition(calories=190, carbs_g=8, sugar_g=2, protein_g=10, fat_g=12, sodium_mg=80, fiber_g=2),
        price_tier="budget",
        health_tags=["lower_sugar", "heart_health"],
    ),
)


def normalize_catalog_text(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum() or ch.isspace()).strip()


def list_default_catalog(*, locale: str = "en-SG") -> list[MealCatalogItem]:
    return [item for item in DEFAULT_MEAL_CATALOG if item.locale == locale and item.active]


def find_catalog_item_by_title(title: str, *, locale: str = "en-SG") -> MealCatalogItem | None:
    needle = normalize_catalog_text(title)
    for item in list_default_catalog(locale=locale):
        if needle == normalize_catalog_text(item.title):
            return item
    for item in list_default_catalog(locale=locale):
        if needle in normalize_catalog_text(item.title) or normalize_catalog_text(item.title) in needle:
            return item
    return None


__all__ = [
    "DEFAULT_MEAL_CATALOG",
    "find_catalog_item_by_title",
    "list_default_catalog",
    "normalize_catalog_text",
]
