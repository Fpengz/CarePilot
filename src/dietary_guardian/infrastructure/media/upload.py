"""Image upload preprocessing and ``ImageInput`` construction.

Handles MIME-type validation, optional downscaling via Pillow, and wraps the
result in an ``ImageInput`` ready for the vision agent.
"""

from io import BytesIO
from typing import Protocol

from PIL import Image, ImageOps, UnidentifiedImageError

from dietary_guardian.infrastructure.media.ingestion import compute_content_sha256
from dietary_guardian.infrastructure.observability import get_logger
from dietary_guardian.domain.meals.models import ImageInput

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
logger = get_logger(__name__)


class UploadedFileLike(Protocol):
    name: str
    type: str

    def getvalue(self) -> bytes: ...


def _estimate_multi_item_count(filename: str | None) -> int:
    if not filename:
        return 1
    # Lightweight heuristic for local cuisine plates (e.g. "rice_fish_veg.jpg")
    base = filename.rsplit(".", 1)[0]
    tokens = [tok for tok in base.replace("-", "_").split("_") if tok]
    return max(1, min(4, len(tokens)))


def _maybe_downscale_image(
    payload: bytes,
    mime_type: str,
    *,
    enabled: bool,
    max_side_px: int,
) -> tuple[bytes, dict[str, str]]:
    metadata: dict[str, str] = {
        "downscaled": "false",
        "original_bytes": str(len(payload)),
    }
    if not enabled:
        return payload, metadata

    try:
        with Image.open(BytesIO(payload)) as img:
            normalized = ImageOps.exif_transpose(img)
            width, height = normalized.size
            metadata["original_width"] = str(width)
            metadata["original_height"] = str(height)
            longest = max(width, height)
            if longest <= max_side_px:
                metadata["downscale_reason"] = "below_threshold"
                return payload, metadata

            scale = max_side_px / float(longest)
            new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            resized = normalized.copy()
            resized.thumbnail(new_size, Image.Resampling.LANCZOS)

            out = BytesIO()
            save_format = {
                "image/jpeg": "JPEG",
                "image/png": "PNG",
                "image/webp": "WEBP",
            }.get(mime_type, "JPEG")
            resized.save(out, format=save_format)
            resized_bytes = out.getvalue()
            metadata.update(
                {
                    "downscaled": "true",
                    "resized_width": str(resized.size[0]),
                    "resized_height": str(resized.size[1]),
                    "resized_bytes": str(len(resized_bytes)),
                    "max_side_px": str(max_side_px),
                }
            )
            logger.info(
                "build_image_input_downscaled mime_type=%s original=%sx%s resized=%sx%s bytes_before=%s bytes_after=%s max_side_px=%s",
                mime_type,
                width,
                height,
                resized.size[0],
                resized.size[1],
                len(payload),
                len(resized_bytes),
                max_side_px,
            )
            return resized_bytes, metadata
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        logger.warning(
            "build_image_input_downscale_skipped mime_type=%s reason=%s",
            mime_type,
            exc,
        )
        metadata["downscale_reason"] = "decode_failed"
        return payload, metadata


def build_image_input(
    uploaded_file: UploadedFileLike | None,
    camera_file: UploadedFileLike | None,
    *,
    downscale_enabled: bool = False,
    max_side_px: int = 1024,
) -> tuple[ImageInput | None, str | None]:
    """Validate, optionally downscale, and wrap an uploaded image as ``ImageInput``."""
    candidate = uploaded_file or camera_file
    if candidate is None:
        logger.info("build_image_input_no_candidate")
        return None, "Please upload a meal photo or take one with camera."

    mime_type = candidate.type or ""
    if mime_type not in SUPPORTED_IMAGE_TYPES:
        logger.warning("build_image_input_unsupported_type mime_type=%s", mime_type)
        return (
            None,
            "Unsupported image format. Please use JPG, PNG, or WEBP.",
        )

    raw_payload = candidate.getvalue()
    payload, preprocess_meta = _maybe_downscale_image(
        raw_payload,
        mime_type,
        enabled=downscale_enabled,
        max_side_px=max_side_px,
    )
    if not payload:
        logger.warning("build_image_input_empty_payload filename=%s", getattr(candidate, "name", None))
        return None, "Image file is empty. Please retake or re-upload."

    source = "upload" if uploaded_file is not None else "camera"
    filename = getattr(candidate, "name", None)
    image_input = ImageInput(
        source=source,
        filename=filename,
        mime_type=mime_type,
        content=payload,
        metadata={
            "multi_item_count": str(_estimate_multi_item_count(filename)),
            "content_sha256": compute_content_sha256(payload),
            **preprocess_meta,
        },
    )
    logger.info(
        "build_image_input_success source=%s filename=%s mime_type=%s bytes=%s multi_item_count=%s",
        image_input.source,
        image_input.filename,
        image_input.mime_type,
        len(image_input.content),
        image_input.metadata.get("multi_item_count"),
    )
    return image_input, None


__all__ = ["UploadedFileLike", "build_image_input"]
