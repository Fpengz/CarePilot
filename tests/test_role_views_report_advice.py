from dietary_guardian.models.recommendation import RecommendationOutput
from dietary_guardian.services.dashboard_service import build_role_report_advice_view


def test_role_report_advice_views() -> None:
    rec = RecommendationOutput(
        safe=True,
        rationale="Biomarker grounded advice",
        localized_advice=["Try fish soup"],
    )
    assert "fish soup" in build_role_report_advice_view("patient", rec)["message"].lower()
    assert "biomarker" in build_role_report_advice_view("caregiver", rec)["message"].lower()
