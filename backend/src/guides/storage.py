"""EDO yo'riqnomasi videosini BO'LAKLAB yuklash.

Nima uchun bo'laklab: nginx har bir so'rov tanasini 10 MB bilan cheklaydi,
video esa 200 MB gacha. nginx sozlamasiga tegmaslik uchun frontend faylni
8 MB lik bo'laklarga bo'lib, ketma-ket yuboradi:

  1) start      — bo'sh vaqtinchalik fayl ochiladi, `upload_id` qaytadi;
  2) append     — har bir bo'lak `offset` bilan oxiriga qo'shiladi;
  3) finalize   — fayl MP4 ekani va hajmi tekshiriladi, doimiy joyga ko'chadi.

`offset` — mijoz shu bo'lakni fayl qayerdan boshlanadi deb hisoblayotgani.
U diskdagi joriy hajmga teng bo'lmasa bo'lak qabul qilinmaydi: tarmoq uzilib,
bo'lak qayta yuborilsa ham fayl ichida ikki marta yozilib qolmaydi.

Vaqtinchalik fayllar `edo_guides/tmp/` da; tashlab ketilgan yuklashlar
(24 soatdan eski) keyingi yuklash boshlanganda o'chiriladi.
"""

import time
from pathlib import Path
from uuid import UUID, uuid4

import anyio

from loggers import get_logger
from src.core.errors.exceptions import (
    InfrastructureException,
    InstanceNotFoundException,
    InstanceProcessingException,
    NotAcceptableException,
    PayloadTooLargeException,
)
from src.core.storage.media import media_root
from src.core.utils.datetime_utils import get_utc_now

logger = get_logger(__name__)

VIDEO_SUBDIR = "edo_guides"
TMP_SUBDIR = "edo_guides/tmp"
STALE_SECONDS = 24 * 60 * 60

UPLOAD_NOT_FOUND = "Yuklash topilmadi yoki muddati o'tgan"
BAD_OFFSET = "Bo'lak tartibi buzildi — yuklashni qaytadan boshlang"
BAD_VIDEO = "Faqat MP4 video yuklash mumkin"
TOO_LARGE = "Fayl hajmi juda katta"
EMPTY_CHUNK = "Bo'sh bo'lak"
WRITE_FAILED = "Faylni saqlab bo'lmadi"


def looks_like_mp4(head: bytes) -> bool:
    # MP4 (ISO BMFF): 4-8 baytlarda "ftyp". Kengaytma yoki Content-Type
    # mijozdan keladi — faylning o'zini tekshiramiz.
    return len(head) >= 8 and head[4:8] == b"ftyp"


def _tmp_path(upload_id: UUID) -> Path:
    # upload_id UUID sifatida keladi — yo'lga begona belgi tushmaydi
    return media_root() / TMP_SUBDIR / f"{upload_id}.part"


def _cleanup_stale(tmp_dir: Path) -> None:
    if not tmp_dir.is_dir():
        return
    limit = time.time() - STALE_SECONDS
    for part in tmp_dir.glob("*.part"):
        try:
            if part.stat().st_mtime < limit:
                part.unlink(missing_ok=True)
        except OSError:
            pass


def _start(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _cleanup_stale(path.parent)
    path.touch(exist_ok=False)


async def start_upload() -> UUID:
    upload_id = uuid4()
    try:
        await anyio.to_thread.run_sync(_start, _tmp_path(upload_id))
    except OSError as error:
        logger.exception("Video yuklashni boshlab bo'lmadi")
        raise InfrastructureException(WRITE_FAILED) from error
    return upload_id


def _append(path: Path, offset: int, data: bytes, max_total: int) -> int:
    if not path.is_file():
        raise InstanceNotFoundException(UPLOAD_NOT_FOUND)
    current = path.stat().st_size
    if offset != current:
        raise InstanceProcessingException(BAD_OFFSET)
    if current == 0 and not looks_like_mp4(data[:8]):
        # Birinchi bo'lakdayoq aniqlanadi — 200 MB yuklab bo'lgach emas
        path.unlink(missing_ok=True)
        raise NotAcceptableException(BAD_VIDEO)
    if current + len(data) > max_total:
        path.unlink(missing_ok=True)
        raise PayloadTooLargeException(TOO_LARGE)
    with path.open("ab") as out:
        out.write(data)
    return current + len(data)


async def append_chunk(
    upload_id: UUID, offset: int, data: bytes, max_total: int
) -> int:
    """Bo'lakni qo'shadi va faylning yangi hajmini qaytaradi."""
    if not data:
        raise InstanceProcessingException(EMPTY_CHUNK)
    try:
        return await anyio.to_thread.run_sync(
            _append, _tmp_path(upload_id), offset, data, max_total
        )
    except OSError as error:
        logger.exception("Video bo'lagini yozib bo'lmadi: %s", upload_id)
        raise InfrastructureException(WRITE_FAILED) from error


def _finalize(src: Path, relative: Path) -> int:
    if not src.is_file():
        raise InstanceNotFoundException(UPLOAD_NOT_FOUND)
    size = src.stat().st_size
    with src.open("rb") as f:
        if not looks_like_mp4(f.read(8)):
            src.unlink(missing_ok=True)
            raise NotAcceptableException(BAD_VIDEO)
    target = media_root() / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    # Bitta volume ichida — nusxalashsiz, bir zumda
    src.replace(target)
    return size


async def finalize_upload(upload_id: UUID) -> tuple[str, int]:
    """Yig'ilgan faylni doimiy joyga ko'chiradi: (nisbiy yo'l, hajm)."""
    now = get_utc_now()
    relative = Path(VIDEO_SUBDIR) / f"{now:%Y}" / f"{now:%m}" / f"{uuid4()}.mp4"
    try:
        size = await anyio.to_thread.run_sync(
            _finalize, _tmp_path(upload_id), relative
        )
    except OSError as error:
        logger.exception("Videoni saqlab bo'lmadi: %s", upload_id)
        raise InfrastructureException(WRITE_FAILED) from error
    logger.info("Video saqlandi: %s (%s bayt)", relative, size)
    return relative.as_posix(), size


async def cancel_upload(upload_id: UUID) -> None:
    await anyio.to_thread.run_sync(_tmp_path(upload_id).unlink, True)
