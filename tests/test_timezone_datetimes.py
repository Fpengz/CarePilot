from datetime import timezone

from dietary_guardian.domain.health.models import ReportInput
from dietary_guardian.models.meal import MealState, Nutrition
from dietary_guardian.models.meal_record import MealRecognitionRecord
from dietary_guardian.domain.reports import parse_report_input


def _sample_meal_state() -> MealState:
    return MealState(
        dish_name="Test Dish",
        identification_method="AI_Flash",
        ingredients=[],
        nutrition=Nutrition(
            calories=100.0,
            carbs_g=20.0,
            sugar_g=1.0,
            protein_g=5.0,
            fat_g=2.0,
            sodium_mg=200.0,
        ),
        confidence_score=0.8,
        suggested_modifications=[],
    )


def test_meal_record_default_captured_at_is_timezone_aware() -> None:
    record = MealRecognitionRecord(
        id="rec-1",
        user_id="u-1",
        source="upload",
        meal_state=_sample_meal_state(),
    )

    assert record.captured_at.tzinfo is not None
    assert record.captured_at.utcoffset() == timezone.utc.utcoffset(record.captured_at)


def test_report_input_default_uploaded_at_is_timezone_aware() -> None:
    report = ReportInput(source="pasted_text", text="HbA1c: 6.7")

    assert report.uploaded_at.tzinfo is not None
    assert report.uploaded_at.utcoffset() == timezone.utc.utcoffset(report.uploaded_at)


def test_report_parser_measured_at_is_timezone_aware() -> None:
    readings = parse_report_input(ReportInput(source="pasted_text", text="LDL: 4.2"))
    assert readings
    assert readings[0].measured_at is not None
    assert readings[0].measured_at.tzinfo is not None
    assert readings[0].measured_at.utcoffset() == timezone.utc.utcoffset(readings[0].measured_at)
