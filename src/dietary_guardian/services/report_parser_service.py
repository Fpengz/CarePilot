import re
from datetime import datetime, timezone

from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.report import BiomarkerReading, ClinicalProfileSnapshot, ReportInput

logger = get_logger(__name__)
SUPPORTED_BIOMARKER_PATTERNS: dict[str, list[str]] = {
    "hba1c": [r"hba1c", r"glycated\s+hemoglobin"],
    "fasting_glucose": [r"fasting\s+glucose", r"glucose"],
    "ldl": [r"ldl"],
    "hdl": [r"hdl"],
    "triglycerides": [r"triglycerides?", r"tg"],
    "systolic_bp": [r"systolic\s*bp", r"sbp"],
    "diastolic_bp": [r"diastolic\s*bp", r"dbp"],
    "creatinine": [r"creatinine"],
}


def _extract_text(report_input: ReportInput) -> str:
    if report_input.source == "pasted_text":
        text = report_input.text or ""
        logger.debug("extract_report_text source=pasted_text chars=%s", len(text))
        return text
    if report_input.content_bytes is None:
        logger.warning("extract_report_text source=pdf no_content_bytes")
        return ""
    # Lightweight PDF fallback: decode bytes and search visible tokens.
    decoded = report_input.content_bytes.decode("latin-1", errors="ignore")
    logger.debug(
        "extract_report_text source=pdf bytes=%s decoded_chars=%s",
        len(report_input.content_bytes),
        len(decoded),
    )
    return decoded


def _extract_value(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        regex = re.compile(rf"(?:{pattern})\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
        match = regex.search(text)
        if match:
            return float(match.group(1))
    return None


def parse_report_input(report_input: ReportInput) -> list[BiomarkerReading]:
    logger.info("parse_report_input_start source=%s", report_input.source)
    text = _extract_text(report_input)
    readings: list[BiomarkerReading] = []
    for canonical_name, patterns in SUPPORTED_BIOMARKER_PATTERNS.items():
        value = _extract_value(text, patterns)
        if value is None:
            continue
        readings.append(
            BiomarkerReading(
                name=canonical_name,
                value=value,
                measured_at=datetime.now(timezone.utc),
                source_doc_id="uploaded_report",
            )
        )
    logger.info("parse_report_input_complete source=%s readings=%s", report_input.source, len(readings))
    return readings


def build_clinical_snapshot(readings: list[BiomarkerReading]) -> ClinicalProfileSnapshot:
    biomarkers = {r.name: r.value for r in readings}
    flags: list[str] = []
    if biomarkers.get("hba1c", 0) >= 6.5:
        flags.append("high_hba1c")
    if biomarkers.get("ldl", 0) >= 3.4:
        flags.append("high_ldl")
    systolic = biomarkers.get("systolic_bp")
    diastolic = biomarkers.get("diastolic_bp")
    if systolic is not None and diastolic is not None and (systolic >= 140 or diastolic >= 90):
        flags.append("high_bp")
    snapshot = ClinicalProfileSnapshot(biomarkers=biomarkers, risk_flags=flags)
    logger.info(
        "build_clinical_snapshot biomarkers=%s risk_flags=%s",
        sorted(snapshot.biomarkers.keys()),
        snapshot.risk_flags,
    )
    return snapshot
