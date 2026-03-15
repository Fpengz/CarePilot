"""Source adapters for medication intake text and uploads."""

from __future__ import annotations

import hashlib

from .models import MedicationIntakeSource


def _source_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_plain_text_source(instructions_text: str) -> MedicationIntakeSource:
    normalized = instructions_text.strip()
    return MedicationIntakeSource(
        source_type="plain_text",
        extracted_text=normalized,
        source_hash=_source_hash(normalized.encode("utf-8")),
    )


def extract_upload_source(
    *, filename: str, mime_type: str, content: bytes
) -> MedicationIntakeSource:
    if mime_type.startswith("text/"):
        extracted = content.decode("utf-8", errors="ignore")
    else:
        # Lightweight document fallback for hackathon MVP: decode visible tokens from bytes.
        extracted = content.decode("latin-1", errors="ignore")
    return MedicationIntakeSource(
        source_type="upload",
        extracted_text=extracted.strip(),
        filename=filename,
        mime_type=mime_type,
        source_hash=_source_hash(content),
    )
