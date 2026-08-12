"""Local media storage for user-uploaded images.

Files are written under ``config.app.MEDIA_ROOT`` and never served by a static
mount: every read goes through an authenticated endpoint, so an uploaded
screenshot can only be opened by someone allowed to see the report it belongs
to. Only the relative path is stored in the database.
"""

from io import BytesIO
from pathlib import Path
from uuid import uuid4

import anyio
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from loggers import get_logger
from src.core.errors.exceptions import (
    InfrastructureException,
    InstanceProcessingException,
    NotAcceptableException,
    PayloadTooLargeException,
)
from src.core.utils.datetime_utils import get_utc_now
from src.main.config import config

logger = get_logger(__name__)

CHUNK_SIZE = 64 * 1024

# Accepted image types and the extension used when writing the file. The
# extension is derived from the format Pillow actually detects, never from the
# client-supplied filename.
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}
FORMAT_EXTENSIONS = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}

TOO_LARGE = "Fayl hajmi juda katta"
BAD_TYPE = "Faqat PNG, JPG yoki WEBP rasm yuklash mumkin"
BAD_IMAGE = "Faylni rasm sifatida o'qib bo'lmadi"
WRITE_FAILED = "Faylni saqlab bo'lmadi"


def media_root() -> Path:
    return Path(config.app.MEDIA_ROOT)


def resolve_media_path(relative_path: str) -> Path:
    """Resolve a stored relative path, refusing anything outside MEDIA_ROOT.

    The stored value always comes from ``save_image``, but resolving defensively
    keeps a tampered database row from turning into an arbitrary file read.
    """
    root = media_root().resolve()
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root):
        raise InstanceProcessingException("Fayl yo'li noto'g'ri")
    return candidate


async def read_upload_limited(upload: UploadFile, max_bytes: int) -> bytes:
    """Read an upload into memory, refusing anything over ``max_bytes``.

    Use this instead of a bare ``await upload.read()``: the latter buffers the
    WHOLE body before anyone can object, so a single large (or deliberately
    huge) file can exhaust the worker's memory.

    Here the body arrives in 64 KB chunks and the limit is checked after each
    one, so an oversized upload is rejected after ~64 KB rather than after
    however many hundred megabytes the client decided to send.

    Raises:
        PayloadTooLargeException: the upload exceeds ``max_bytes``.
    """
    buffer = bytearray()
    while chunk := await upload.read(CHUNK_SIZE):
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise PayloadTooLargeException(TOO_LARGE)
    return bytes(buffer)


async def save_image(
    upload: UploadFile, subdir: str, max_bytes: int
) -> tuple[str, int]:
    """Validate and store an uploaded image.

    Returns the path relative to MEDIA_ROOT (e.g. ``reports/2026/08/<uuid>.png``)
    and the size in bytes.

    Raises:
        PayloadTooLargeException: the upload exceeds ``max_bytes``.
        NotAcceptableException: wrong content type, or the bytes are not a
            supported image regardless of the declared type.
    """
    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise NotAcceptableException(BAD_TYPE)

    # Read in chunks so an oversized upload is rejected without buffering all
    # of it first.
    buffer = bytearray()
    while chunk := await upload.read(CHUNK_SIZE):
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise PayloadTooLargeException(TOO_LARGE)
    data = bytes(buffer)
    if not data:
        raise NotAcceptableException(BAD_IMAGE)

    # Content-Type is client-supplied; verify the actual bytes.
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
            image_format = image.format or ""
    except (UnidentifiedImageError, OSError, ValueError):
        raise NotAcceptableException(BAD_IMAGE) from None

    extension = FORMAT_EXTENSIONS.get(image_format)
    if extension is None:
        raise NotAcceptableException(BAD_TYPE)

    now = get_utc_now()
    relative_dir = Path(subdir) / f"{now:%Y}" / f"{now:%m}"
    relative_path = relative_dir / f"{uuid4()}.{extension}"
    target = media_root() / relative_path

    try:
        await anyio.to_thread.run_sync(_write_file, target, data)
    except OSError as error:
        # Odatda MEDIA_ROOT ga yozish huquqi yo'q (Docker volume egasi noto'g'ri).
        # Xom 500 o'rniga tushunarli xabar qaytaramiz.
        logger.exception("Rasmni saqlab bo'lmadi: %s", target)
        raise InfrastructureException(WRITE_FAILED) from error

    logger.info("Rasm saqlandi: %s (%s bayt)", relative_path, len(data))
    return relative_path.as_posix(), len(data)


def _write_file(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


async def delete_image(relative_path: str) -> None:
    """Remove a stored image; a missing file is not an error."""
    try:
        path = resolve_media_path(relative_path)
    except InstanceProcessingException:
        return
    await anyio.to_thread.run_sync(path.unlink, True)
