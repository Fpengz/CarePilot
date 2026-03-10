from datetime import datetime

from dietary_guardian.domain.health.models import ReportInput
from dietary_guardian.domain.identity.models import (
    MedicalCondition,
    Medication,
    UserProfile,
)
from dietary_guardian.models.meal import MealState, Nutrition
from dietary_guardian.models.meal_record import MealRecognitionRecord
from dietary_guardian.domain.recommendations.meal_recommendations import generate_recommendation
from dietary_guardian.domain.reports import (
    build_clinical_snapshot,
    parse_report_input,
)


def test_user_story_3_report_to_grounded_recommendation() -> None:
    report = ReportInput(source="pasted_text", text="HbA1c 7.2 LDL 4.1")
    readings = parse_report_input(report)
    snapshot = build_clinical_snapshot(readings)

    user = UserProfile(
        id="u1",
        name="Mr Tan",
        age=68,
        conditions=[MedicalCondition(name="Diabetes", severity="High")],
        medications=[Medication(name="Metformin", dosage="500mg")],
    )
    meal_record = MealRecognitionRecord(
        id="m1",
        user_id="u1",
        captured_at=datetime(2026, 2, 24, 12, 0),
        source="upload",
        meal_state=MealState(
            dish_name="Laksa",
            confidence_score=0.95,
            identification_method="AI_Flash",
            ingredients=[],
            nutrition=Nutrition(calories=590, carbs_g=60, sugar_g=6, protein_g=20, fat_g=30, sodium_mg=1500),
        ),
    )
    recommendation = generate_recommendation(meal_record, snapshot, user)
    assert recommendation.safe is True
    assert "hba1c=7.2" in recommendation.rationale.lower()
