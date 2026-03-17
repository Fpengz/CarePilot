"""Tests for patient medical card markdown formatting."""

from __future__ import annotations

from datetime import UTC, date, datetime

from care_pilot.features.companion.core.domain import CaseSnapshot, EvidenceBundle, EvidenceCitation
from care_pilot.features.companion.core.health.models import (
    BloodPressureStats,
    BloodPressureSummary,
    BloodPressureTrend,
)
from care_pilot.features.companion.patient_card import patient_card_service


def test_build_patient_summary_formats_bp_to_two_decimals() -> None:
    stats = BloodPressureStats(
        avg_systolic=137.1099,
        avg_diastolic=89.4444,
        min_systolic=135.1070058986298,
        max_systolic=139.04896062092675,
        min_diastolic=86.12946316617032,
        max_diastolic=92.76748055480721,
        total_readings=5,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 7),
    )
    bp_summary = BloodPressureSummary(
        stats=stats,
        trend=BloodPressureTrend(direction="increase", delta_systolic=1.2),
        target_systolic=130,
        target_diastolic=80,
    )
    snapshot = CaseSnapshot(
        user_id="user-1",
        profile_name="Auntie Mei",
        conditions=["hypertension"],
        medications=["amlodipine"],
        blood_pressure_summary=bp_summary,
        generated_at=datetime.now(UTC),
    )

    summary = patient_card_service._build_patient_summary(snapshot)

    assert "Avg BP: 137.11/89.44 mmHg (range 135.11-139.05 / 86.13-92.77)" in summary


def test_finalize_markdown_appends_references_and_disclaimer() -> None:
    evidence = EvidenceBundle(
        query="hypertension",
        citations=[
            EvidenceCitation(
                title="Treatment of hypertension in patients with diabetes mellitus",
                summary="Hypertension occurs frequently in patients with diabetes.",
                relevance="clinical",
                confidence=0.8,
                url="https://example.com/hypertension",
            )
        ],
    )

    markdown = patient_card_service._finalize_markdown("## Data Overview\n- Patient: Mei", evidence)

    assert "## References" in markdown
    assert (
        "- [Treatment of hypertension in patients with diabetes mellitus](https://example.com/hypertension): "
        "Hypertension occurs frequently in patients with diabetes."
        in markdown
    )
    assert markdown.rstrip().endswith(patient_card_service._DISCLAIMER)
