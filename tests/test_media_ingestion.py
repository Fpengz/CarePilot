"""Tests for media ingestion."""

from datetime import datetime, timezone

from dietary_guardian.domain.meals.models import ImageInput
from dietary_guardian.infrastructure.media.ingestion import (
    build_capture_envelope,
    should_suppress_duplicate_capture,
)


def test_build_capture_envelope_generates_content_hash() -> None:
    image = ImageInput(
        source="upload",
        filename="meal.jpg",
        mime_type="image/jpeg",
        content=b"abc123",
        metadata={"foo": "bar"},
    )

    envelope = build_capture_envelope(image, user_id="u1")

    assert envelope.modality == "image"
    assert envelope.content_sha256
    assert envelope.metadata["foo"] == "bar"
    assert envelope.user_id == "u1"


def test_duplicate_capture_suppression_uses_content_hash_and_window() -> None:
    image = ImageInput(
        source="camera",
        filename="cam.jpg",
        mime_type="image/jpeg",
        content=b"same-bytes",
    )
    envelope = build_capture_envelope(image, user_id="u1")
    session_state: dict[str, str] = {}

    first = should_suppress_duplicate_capture(session_state, envelope, window_seconds=30)
    second = should_suppress_duplicate_capture(session_state, envelope, window_seconds=30)

    assert first is False
    assert second is True


def test_duplicate_capture_suppression_expires_after_window() -> None:
    image = ImageInput(
        source="camera",
        filename="cam.jpg",
        mime_type="image/jpeg",
        content=b"same-bytes",
    )
    envelope = build_capture_envelope(image, user_id="u1")
    session_state = {
        "capture_dedupe:default": {
            envelope.content_sha256: datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat(),
        }
    }

    suppress = should_suppress_duplicate_capture(session_state, envelope, window_seconds=1)

    assert suppress is False

