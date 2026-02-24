from typing import Protocol

from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.meal import ImageInput

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


def build_image_input(
    uploaded_file: UploadedFileLike | None,
    camera_file: UploadedFileLike | None,
) -> tuple[ImageInput | None, str | None]:
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

    payload = candidate.getvalue()
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
        metadata={"multi_item_count": str(_estimate_multi_item_count(filename))},
    )
    logger.info(
        "build_image_input_success source=%s filename=%s mime_type=%s bytes=%s multi_item_count=%s",
        image_input.source,
        image_input.filename,
        image_input.mime_type,
        len(image_input.content),
        image_input.metadata.get("multi_item_count"),
    )
    return (
        image_input,
        None,
    )
