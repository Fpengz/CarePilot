"""Canonical storage platform exports."""

from dietary_guardian.platform.storage.media.ingestion import build_capture_envelope, should_suppress_duplicate_capture
from dietary_guardian.platform.storage.media.upload import SUPPORTED_IMAGE_TYPES, _maybe_downscale_image

__all__ = [
    "SUPPORTED_IMAGE_TYPES",
    "_maybe_downscale_image",
    "build_capture_envelope",
    "should_suppress_duplicate_capture",
]
