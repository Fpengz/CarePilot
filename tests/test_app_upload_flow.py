from dataclasses import dataclass
from io import BytesIO

from PIL import Image

from dietary_guardian.models.meal import ImageInput
from dietary_guardian.services.upload_service import build_image_input


@dataclass
class FakeUploadedFile:
    name: str
    type: str
    payload: bytes

    def getvalue(self) -> bytes:
        return self.payload


def test_build_image_input_from_upload() -> None:
    uploaded = FakeUploadedFile("meal.jpg", "image/jpeg", b"\xff\xd8\xff")
    image_input, error = build_image_input(uploaded, None)

    assert error is None
    assert isinstance(image_input, ImageInput)
    assert image_input.source == "upload"
    assert image_input.filename == "meal.jpg"
    assert image_input.mime_type == "image/jpeg"


def test_build_image_input_from_camera() -> None:
    camera = FakeUploadedFile("camera.png", "image/png", b"\x89PNG")
    image_input, error = build_image_input(None, camera)

    assert error is None
    assert isinstance(image_input, ImageInput)
    assert image_input.source == "camera"
    assert image_input.filename == "camera.png"


def test_build_image_input_rejects_unsupported_type() -> None:
    uploaded = FakeUploadedFile("meal.gif", "image/gif", b"GIF89a")
    image_input, error = build_image_input(uploaded, None)

    assert image_input is None
    assert error is not None
    assert "Unsupported image format" in error


def test_build_image_input_downscales_when_enabled() -> None:
    img = Image.new("RGB", (2000, 1000), color=(255, 0, 0))

    buf = BytesIO()
    img.save(buf, format="JPEG")
    uploaded = FakeUploadedFile("meal_large.jpg", "image/jpeg", buf.getvalue())

    image_input, error = build_image_input(
        uploaded,
        None,
        downscale_enabled=True,
        max_side_px=512,
    )

    assert error is None
    assert isinstance(image_input, ImageInput)
    assert image_input.metadata["downscaled"] == "true"
    assert int(image_input.metadata["resized_width"]) <= 512
    assert int(image_input.metadata["resized_height"]) <= 512


def test_build_image_input_keeps_original_when_downscale_disabled() -> None:
    img = Image.new("RGB", (1200, 800), color=(0, 255, 0))

    buf = BytesIO()
    img.save(buf, format="JPEG")
    payload = buf.getvalue()
    uploaded = FakeUploadedFile("meal_large.jpg", "image/jpeg", payload)

    image_input, error = build_image_input(
        uploaded,
        None,
        downscale_enabled=False,
        max_side_px=512,
    )

    assert error is None
    assert isinstance(image_input, ImageInput)
    assert image_input.content == payload
    assert image_input.metadata["downscaled"] == "false"


def test_build_image_input_downscale_applies_exif_orientation() -> None:
    img = Image.new("RGB", (2000, 1000), color=(0, 0, 255))
    exif = Image.Exif()
    exif[274] = 6  # Rotate 90° CW for display
    buf = BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    uploaded = FakeUploadedFile("meal_rotated.jpg", "image/jpeg", buf.getvalue())

    image_input, error = build_image_input(
        uploaded,
        None,
        downscale_enabled=True,
        max_side_px=512,
    )

    assert error is None
    assert isinstance(image_input, ImageInput)

    with Image.open(BytesIO(image_input.content)) as out:
        assert out.size == (256, 512)
