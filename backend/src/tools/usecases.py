from dataclasses import dataclass
from pathlib import Path

from anyio import to_thread
from fastapi import UploadFile

from loggers import get_logger
from src.core.errors.exceptions import InstanceProcessingException
from src.core.storage.media import read_upload_limited
from src.main.config import config
from src.tools.pdf_convert import (
    IMAGE_EXTS,
    OFFICE_EXTS,
    file_ext,
    images_to_pdf,
    office_to_pdf,
)

logger = get_logger(__name__)

# Bitta PDF'ga yig'iladigan rasmlar soni
MAX_IMAGES = 20


@dataclass(frozen=True, slots=True)
class ConvertResult:
    content: bytes
    filename: str


class ConvertToPdfUseCase:
    """
    Fayl(lar)ni PDF'ga o'giradi. Qoidalar:

    * BITTA ofis hujjati (Word/Excel/PowerPoint/ODF/RTF) — yoki
    * 1..20 ta RASM — hammasi yuborilgan tartibda bitta PDF'ga yig'iladi.

    Hujjat va rasmni aralash yuborish, bir nechta hujjatni birga yuborish
    mumkin emas (400). Jami hajm — config.app.CONVERT_MAX_BYTES (413).
    """

    async def execute(self, files: list[UploadFile]) -> ConvertResult:
        if not files:
            raise InstanceProcessingException("Fayl yuborilmadi")

        exts = [file_ext(f.filename) for f in files]
        unsupported = [e for e in exts if e not in IMAGE_EXTS | OFFICE_EXTS]
        if unsupported:
            raise InstanceProcessingException(
                f"Bu format qo'llab-quvvatlanmaydi: .{unsupported[0] or '?'}"
            )

        is_office = [e in OFFICE_EXTS for e in exts]
        if any(is_office) and len(files) > 1:
            raise InstanceProcessingException(
                "Hujjat (Word/Excel/PowerPoint) bittadan o'giriladi — rasmlar bilan aralashtirmang"
            )
        if len(files) > MAX_IMAGES:
            raise InstanceProcessingException(
                f"Bir martada ko'pi bilan {MAX_IMAGES} ta rasm"
            )

        # Jami hajm cheklovi — har fayl qolgan "byudjet" bilan o'qiladi
        budget = config.app.CONVERT_MAX_BYTES
        payloads: list[bytes] = []
        for f in files:
            data = await read_upload_limited(f, budget)
            if not data:
                raise InstanceProcessingException(f"Fayl bo'sh: {f.filename}")
            budget -= len(data)
            payloads.append(data)

        stem = Path(files[0].filename or "file").stem or "file"
        if is_office[0]:
            pdf = await office_to_pdf(
                payloads[0], exts[0], timeout=config.app.CONVERT_TIMEOUT_SECONDS
            )
        else:
            # pymupdf/Pillow CPU'ni band qiladi — event loop to'xtab qolmasin
            pdf = await to_thread.run_sync(images_to_pdf, payloads)

        logger.info(
            "[Convert] %d ta fayl (.%s) -> PDF, %d bayt", len(files), exts[0], len(pdf)
        )
        return ConvertResult(content=pdf, filename=f"{stem}.pdf")


def get_convert_to_pdf_use_case() -> ConvertToPdfUseCase:
    return ConvertToPdfUseCase()
