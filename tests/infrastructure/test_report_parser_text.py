"""Tests for report parser text."""

from dietary_guardian.domain.health.models import ReportInput
from dietary_guardian.domain.reports import parse_report_input


def test_parse_text_report_extracts_key_biomarkers() -> None:
    report = ReportInput(
        source="pasted_text",
        text="HbA1c: 7.1 LDL: 4.2 fasting glucose: 8.9 creatinine: 95",
    )
    readings = parse_report_input(report)
    names = {r.name for r in readings}
    assert "hba1c" in names
    assert "ldl" in names
    assert "fasting_glucose" in names
    assert "creatinine" in names
