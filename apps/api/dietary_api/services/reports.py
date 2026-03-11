"""API orchestration for clinical report parsing and symptom-context enrichment.

Re-exports from :mod:`dietary_guardian.features.reports.service`.
"""

from dietary_guardian.features.reports.service import parse_report_for_session  # noqa: F401

__all__ = ["parse_report_for_session"]
