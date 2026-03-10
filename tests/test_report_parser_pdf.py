from dietary_guardian.domain.health.models import ReportInput
from dietary_guardian.domain.reports import parse_report_input


def test_parse_pdf_like_bytes() -> None:
    fake_pdf_bytes = b"%PDF-1.4 LDL 3.8 HbA1c 6.8 systolic bp 142 diastolic bp 92"
    report = ReportInput(source="pdf", content_bytes=fake_pdf_bytes)
    readings = parse_report_input(report)
    names = {r.name for r in readings}
    assert "ldl" in names
    assert "hba1c" in names
    assert "systolic_bp" in names
    assert "diastolic_bp" in names
