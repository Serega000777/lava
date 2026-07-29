from io import BytesIO

import pytest
from fastapi import HTTPException
from PIL import Image

from app.media.service import first_available_position, normalize_image


def image_bytes(format_name: str = "PNG") -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 24), (120, 30, 10)).save(output, format=format_name)
    return output.getvalue()


def test_image_is_normalized_to_metadata_free_webp() -> None:
    normalized = normalize_image(image_bytes())

    assert normalized.width == 32
    assert normalized.height == 24
    with Image.open(BytesIO(normalized.content)) as result:
        assert result.format == "WEBP"
        assert not result.getexif()


def test_non_image_payload_is_rejected() -> None:
    with pytest.raises(HTTPException) as error:
        normalize_image(b"<script>alert(1)</script>")

    assert error.value.status_code == 422
    assert error.value.detail["code"] == "invalid_image"


def test_unsupported_image_format_is_rejected() -> None:
    with pytest.raises(HTTPException) as error:
        normalize_image(image_bytes("GIF"))

    assert error.value.status_code == 415
    assert error.value.detail["code"] == "unsupported_media_type"


def test_deleted_media_position_is_reused() -> None:
    assert first_available_position([0, 2, 3]) == 1


def test_media_limit_is_rejected() -> None:
    with pytest.raises(HTTPException) as error:
        first_available_position(list(range(10)))

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "media_limit_reached"
