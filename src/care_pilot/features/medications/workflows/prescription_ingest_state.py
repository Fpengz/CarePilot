from __future__ import annotations

from pydantic import BaseModel


class PrescriptionIngestState(BaseModel):
    request_id: str
    correlation_id: str
    user_id: str

    # Input (normalized; no HTTP types)
    prescription_text: str
    source: str = "pasted_text"
