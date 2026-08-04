from io import BytesIO
from pathlib import Path

from PIL import Image
from fastapi import UploadFile
import pytest
from starlette.datastructures import Headers

from src.core.errors.exceptions import (
    InstanceProcessingException,
    NotAcceptableException,
    PayloadTooLargeException,
)
from src.core.storage import media
from src.main.config import config


@pytest.fixture(autouse=True)
def _media_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config.app, "MEDIA_ROOT", str(tmp_path))
    return tmp_path


def png_bytes(size: tuple[int, int] = (1, 1)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (10, 20, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


def make_upload(data: bytes, content_type: str, filename: str = "shot.png") -> UploadFile:
    return UploadFile(
        file=BytesIO(data),
        size=len(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.asyncio
async def test_save_image_writes_file_and_returns_relative_path(
    _media_root: Path,
) -> None:
    data = png_bytes()

    relative_path, size = await media.save_image(
        make_upload(data, "image/png"), subdir="reports", max_bytes=1024 * 1024
    )

    assert relative_path.startswith("reports/")
    assert relative_path.endswith(".png")
    assert size == len(data)
    assert (_media_root / relative_path).read_bytes() == data


@pytest.mark.asyncio
async def test_save_image_rejects_oversized_upload() -> None:
    data = png_bytes((200, 200))

    with pytest.raises(PayloadTooLargeException):
        await media.save_image(
            make_upload(data, "image/png"), subdir="reports", max_bytes=64
        )


@pytest.mark.asyncio
async def test_save_image_rejects_disallowed_content_type() -> None:
    with pytest.raises(NotAcceptableException):
        await media.save_image(
            make_upload(b"%PDF-1.7", "application/pdf", "doc.pdf"),
            subdir="reports",
            max_bytes=1024 * 1024,
        )


@pytest.mark.asyncio
async def test_save_image_rejects_non_image_bytes_declared_as_png() -> None:
    """Content-Type mijozdan keladi — baytlarning o'zi ham tekshiriladi."""
    with pytest.raises(NotAcceptableException):
        await media.save_image(
            make_upload(b"%PDF-1.7 not really an image", "image/png"),
            subdir="reports",
            max_bytes=1024 * 1024,
        )


@pytest.mark.asyncio
async def test_save_image_uses_detected_format_not_client_filename(
    _media_root: Path,
) -> None:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), (1, 2, 3)).save(buffer, format="JPEG")

    relative_path, _ = await media.save_image(
        make_upload(buffer.getvalue(), "image/jpeg", "evil.php"),
        subdir="reports",
        max_bytes=1024 * 1024,
    )

    assert relative_path.endswith(".jpg")


def test_resolve_media_path_blocks_traversal() -> None:
    with pytest.raises(InstanceProcessingException):
        media.resolve_media_path("../../etc/passwd")
