from dietary_guardian.models.recommendation import RecommendationOutput
from dietary_guardian.application.impact.view_helpers import build_profile_mode_report_advice_view


def test_profile_mode_report_advice_views() -> None:
    rec = RecommendationOutput(
        safe=True,
        rationale="Biomarker grounded advice",
        localized_advice=["Try fish soup"],
    )
    assert "fish soup" in build_profile_mode_report_advice_view("self", rec)["message"].lower()
    assert "biomarker" in build_profile_mode_report_advice_view("caregiver", rec)["message"].lower()
