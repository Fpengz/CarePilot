"""Medication intake parsing and source adapters."""

from .document import build_plain_text_source, extract_upload_source
from .models import (
    LLMNormalizedMedicationInstruction,
    MedicationInferenceEngineProtocol,
    MedicationIntakeDraft,
    MedicationIntakeParseResult,
    MedicationIntakeSource,
    MedicationParseOutput,
    MedicationParseOutputLoose,
    NormalizedMedicationInstruction,
)
from .parser import parse_medication_instructions

__all__ = [
    "MedicationInferenceEngineProtocol",
    "MedicationIntakeDraft",
    "MedicationIntakeParseResult",
    "MedicationIntakeSource",
    "MedicationParseOutput",
    "MedicationParseOutputLoose",
    "LLMNormalizedMedicationInstruction",
    "NormalizedMedicationInstruction",
    "build_plain_text_source",
    "extract_upload_source",
    "parse_medication_instructions",
]
