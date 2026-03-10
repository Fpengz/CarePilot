from dietary_guardian.domain.health.models import BiomarkerReading
from dietary_guardian.domain.reports import build_clinical_snapshot


def test_build_snapshot_sets_risk_flags() -> None:
    snapshot = build_clinical_snapshot(
        [
            BiomarkerReading(name="hba1c", value=7.0),
            BiomarkerReading(name="ldl", value=4.0),
            BiomarkerReading(name="systolic_bp", value=145),
            BiomarkerReading(name="diastolic_bp", value=95),
        ]
    )
    assert "high_hba1c" in snapshot.risk_flags
    assert "high_ldl" in snapshot.risk_flags
    assert "high_bp" in snapshot.risk_flags
