from io import BytesIO

import pytest
from PIL import Image

from app.features.profile_avatar.service import AvatarValidationError, process_avatar


def image_bytes(size: tuple[int, int], image_format: str = "PNG") -> bytes:
    image = Image.new("RGB", size, (14, 114, 116))
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


@pytest.mark.parametrize("size", [(900, 500), (500, 900), (600, 600)])
def test_process_avatar_outputs_square_jpeg(size: tuple[int, int]) -> None:
    result = process_avatar(image_bytes(size))
    image = Image.open(BytesIO(result))

    assert image.size == (512, 512)
    assert image.mode == "RGB"
    assert image.format == "JPEG"


def test_process_avatar_rejects_corrupt_content() -> None:
    with pytest.raises(AvatarValidationError, match="inválida"):
        process_avatar(b"not-an-image")


def test_process_avatar_rejects_oversized_upload(monkeypatch) -> None:
    monkeypatch.setattr("app.features.profile_avatar.service.MAX_AVATAR_BYTES", 8)

    with pytest.raises(AvatarValidationError, match="10 MiB"):
        process_avatar(b"123456789")
