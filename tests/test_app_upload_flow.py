from dataclasses import dataclass

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
