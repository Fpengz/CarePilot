"""
backend/routers/medications.py
-------------------------------
Endpoints:
    GET    /api/medications                — list all medications
    POST   /api/medications/manual         — add medication manually
    DELETE /api/medications/{row_id}       — delete by ID
    POST   /api/medications/parse          — preview parse a prescription text
    POST   /api/medications/save-parsed    — parse + save all
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.deps import (
    user_med_db,
    prescription_parser,
    TIMING_LABEL_TO_SLOT,
    SLOT_TO_LABEL,
    TIMING_SLOTS,
)

router = APIRouter(prefix="/api/medications", tags=["medications"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ManualMedRequest(BaseModel):
    name:          str
    dose_notes:    str = ""
    timing_labels: list[str] = []   # e.g. ["Before Breakfast", "After Dinner"]


class ParseRequest(BaseModel):
    text: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
def list_medications():
    """Return all medications as display rows."""
    rows = user_med_db.to_display_rows()
    # rows = [[id, name, dose, schedule, added], ...]
    headers = ["id", "medicine", "dose_notes", "schedule", "added"]
    return {
        "medications": [dict(zip(headers, r)) for r in rows],
        "timing_labels": list(TIMING_LABEL_TO_SLOT.keys()),
    }


@router.post("/manual", status_code=201)
def add_manual(req: ManualMedRequest):
    """Add a medication manually."""
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="name is required")

    slots = [
        TIMING_LABEL_TO_SLOT[lbl]
        for lbl in req.timing_labels
        if lbl in TIMING_LABEL_TO_SLOT
    ]
    user_med_db.add_medication(req.name.strip(), slots, req.dose_notes.strip())
    return {"added": True, "medications": _all_rows()}


@router.delete("/{row_id}")
def delete_medication(row_id: int):
    """Delete a medication by its ID."""
    deleted = user_med_db.delete_medication(row_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No medication with ID {row_id}")
    return {"deleted": True, "id": row_id, "medications": _all_rows()}


@router.post("/parse")
def parse_prescription(req: ParseRequest):
    """Preview-parse a prescription text without saving."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    try:
        entries = prescription_parser.parse(req.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    preview = []
    for e in entries:
        labels = [SLOT_TO_LABEL[s] for s in e.get("timing", []) if s in SLOT_TO_LABEL]
        preview.append({
            "medicine_name": e["medicine_name"],
            "dose_notes":    e.get("dose_notes") or "",
            "timing_labels": labels,
        })
    return {"entries": preview, "count": len(preview)}


@router.post("/save-parsed", status_code=201)
def save_parsed(req: ParseRequest):
    """Parse a prescription text and save all found medications."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    try:
        entries = prescription_parser.parse(req.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    for e in entries:
        timing = [t for t in e.get("timing", []) if t in TIMING_SLOTS]
        user_med_db.add_medication(e["medicine_name"], timing, e.get("dose_notes") or "")

    return {"saved": len(entries), "medications": _all_rows()}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _all_rows():
    headers = ["id", "medicine", "dose_notes", "schedule", "added"]
    return [dict(zip(headers, r)) for r in user_med_db.to_display_rows()]
