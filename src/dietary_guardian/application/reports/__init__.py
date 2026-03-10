"""Application reports package.

Re-exports report parsing entry points for use-case callers.
"""

from dietary_guardian.domain.reports import build_clinical_snapshot, parse_report_input

__all__ = ["build_clinical_snapshot", "parse_report_input"]
