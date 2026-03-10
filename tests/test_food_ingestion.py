from pathlib import Path

from dietary_guardian.infrastructure.food.ingestion import (
    load_open_food_facts_records,
    load_usda_records,
)


def test_load_usda_records_reduces_source_payload(tmp_path: Path) -> None:
    path = tmp_path / "usda.json"
    path.write_text(
        """
        [
          {
            "fdc_id": 123,
            "description": "Brown Rice",
            "slot": "lunch",
            "portion_unit": "cup",
            "default_portion_grams": 195,
            "nutrients": {
              "calories": 216,
              "carbohydrates": 45,
              "sugars": 1,
              "protein": 5,
              "fat": 2,
              "sodium": 10,
              "fiber": 4
            }
          }
        ]
        """,
        encoding="utf-8",
    )

    records = load_usda_records(path)

    assert len(records) == 1
    assert records[0].food_id == "usda.123"
    assert records[0].portion_references[0].unit == "cup"
    assert records[0].default_portion_grams == 195


def test_load_open_food_facts_records_reduces_source_payload(tmp_path: Path) -> None:
    path = tmp_path / "off.json"
    path.write_text(
        """
        [
          {
            "code": "abc",
            "product_name": "Sparkling Tea",
            "category": "drink",
            "serving_quantity": 330,
            "serving_size": "1 can (330ml)",
            "nutriments": {
              "energy-kcal_100g": 24,
              "carbohydrates_100g": 5,
              "sugars_100g": 5,
              "proteins_100g": 0,
              "fat_100g": 0,
              "salt_100g": 0.02,
              "fiber_100g": 0
            }
          }
        ]
        """,
        encoding="utf-8",
    )

    records = load_open_food_facts_records(path)

    assert len(records) == 1
    assert records[0].food_id == "off.abc"
    assert records[0].slot == "snack"
    assert records[0].default_portion_grams == 330
    assert records[0].nutrition.calories == 79.2
    assert records[0].nutrition.carbs_g == 16.5
    assert records[0].nutrition.sugar_g == 16.5
    assert records[0].nutrition.sodium_mg == 26.4
