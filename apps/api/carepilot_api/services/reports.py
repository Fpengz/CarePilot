"""API orchestration for clinical report parsing and symptom-context enrichment.

Re-exports from :mod:`care_pilot.features.reports.service`.
"""

from care_pilot.features.reports.service import (
    parse_report_for_session,
)  # noqa: F401

__all__ = ["parse_report_for_session"]
