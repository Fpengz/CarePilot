"""
Provide the reports service entrypoint.

This module exposes the main report ingestion and parsing workflows.
"""

from care_pilot.features.reports.report_application_service import parse_report_for_session

__all__ = ["parse_report_for_session"]
