"""Canonical storage platform exports."""

from care_pilot.platform.storage.media.ingestion import (
    build_capture_envelope,
    should_suppress_duplicate_capture,
)
from care_pilot.platform.storage.media.upload import SUPPORTED_IMAGE_TYPES, _maybe_downscale_image

__all__ = [
    "SUPPORTED_IMAGE_TYPES",
    "_maybe_downscale_image",
    "build_capture_envelope",
    "should_suppress_duplicate_capture",
]
