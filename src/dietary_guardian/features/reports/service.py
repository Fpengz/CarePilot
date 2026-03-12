"""
Provide the reports service entrypoint.

This module exposes the main report ingestion and parsing workflows.
"""

from dietary_guardian.features.reports.use_cases import parse_report_for_session

__all__ = ["parse_report_for_session"]
