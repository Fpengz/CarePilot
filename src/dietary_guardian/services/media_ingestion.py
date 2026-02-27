import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from dietary_guardian.models.contracts import CaptureEnvelope
from dietary_guardian.models.meal import ImageInput


def compute_content_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_capture_envelope(
    image_input: ImageInput,
    *,
    user_id: str | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> CaptureEnvelope:
    content_sha256 = image_input.metadata.get("content_sha256") or compute_content_sha256(image_input.content)
    return CaptureEnvelope(
        capture_id=str(uuid4()),
        request_id=request_id or str(uuid4()),
        correlation_id=correlation_id or str(uuid4()),
        user_id=user_id,
        source=image_input.source,
        modality="image",
        mime_type=image_input.mime_type,
        filename=image_input.filename,
        content_sha256=content_sha256,
        metadata={**image_input.metadata},
        captured_at=datetime.now(timezone.utc),
    )


def should_suppress_duplicate_capture(
    session_state: dict[str, Any],
    envelope: CaptureEnvelope,
    *,
    window_seconds: int = 30,
    session_key: str = "default",
) -> bool:
    key = f"capture_dedupe:{session_key}"
    bucket = session_state.setdefault(key, {})
    if not isinstance(bucket, dict):
        bucket = {}
        session_state[key] = bucket

    content_hash = envelope.content_sha256
    if not content_hash:
        return False

    now = datetime.now(timezone.utc)
    seen_raw = bucket.get(content_hash)
    if isinstance(seen_raw, str):
        try:
            seen_at = datetime.fromisoformat(seen_raw)
            if seen_at.tzinfo is None:
                seen_at = seen_at.replace(tzinfo=timezone.utc)
            if (now - seen_at).total_seconds() <= window_seconds:
                return True
        except ValueError:
            pass
    bucket[content_hash] = now.isoformat()
    return False
