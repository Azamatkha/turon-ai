"""
Boshqa formatlarni PDF'ga o'girish.

* Rasmlar (JPG/PNG/WEBP/BMP/TIFF) — `pymupdf` bilan: har rasm A4 sahifaga
  joylanadi (keng rasm — albom sahifa), bir nechta rasm bitta PDF bo'ladi.
* Ofis hujjatlari (Word/Excel/PowerPoint/ODF/RTF) — backend image'iga
  o'rnatilgan LibreOffice (`soffice --headless --convert-to pdf`) bilan.
  Sof Python bilan buni sifatli qilib bo'lmaydi: jadval, shrift va sahifa
  chegaralari buziladi.

MAXFIYLIK: fayllar diskka faqat LibreOffice uchun vaqtinchalik papkaga
yoziladi va konvertatsiyadan keyin DARHOL o'chiriladi — hech narsa saqlanmaydi.
"""

import asyncio
import io
import shutil
import tempfile
import uuid
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps

from loggers import get_logger
from src.core.errors.exceptions import (
    InfrastructureException,
    InstanceProcessingException,
)

logger = get_logger(__name__)

IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff"}
OFFICE_EXTS = {
    "doc", "docx", "odt", "rtf",   # matn
    "xls", "xlsx", "ods",          # jadval
    "ppt", "pptx", "odp",          # taqdimot
}

# Fayl "boshi" — kengaytma o'zgartirilgan (masalan .exe -> .docx) fayllarni
# LibreOffice'ga yubormaslik uchun.
_ZIP_MAGIC = b"PK\x03\x04"                     # docx/xlsx/pptx/odt/ods/odp
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # eski doc/xls/ppt
_RTF_MAGIC = b"{\\rtf"
_OFFICE_MAGIC = {
    "docx": (_ZIP_MAGIC,), "xlsx": (_ZIP_MAGIC,), "pptx": (_ZIP_MAGIC,),
    "odt": (_ZIP_MAGIC,), "ods": (_ZIP_MAGIC,), "odp": (_ZIP_MAGIC,),
    "doc": (_OLE_MAGIC,), "xls": (_OLE_MAGIC,), "ppt": (_OLE_MAGIC,),
    "rtf": (_RTF_MAGIC,),
}

# A4 (pt) va chekka. Rasm sahifaga proporsiyasini saqlab sig'diriladi.
_A4 = pymupdf.paper_rect("a4")
_MARGIN = 24
# Rasm "bombasi"dan himoya: juda katta o'lchamli rasm xotirani to'ldirmasin
_MAX_IMAGE_PIXELS = 60_000_000

# Bir vaqtda ko'pi bilan shuncha LibreOffice jarayoni — har biri ~150-300 MB
# xotira oladi, server chat (Ollama/RAG) bilan ham band.
_OFFICE_SEMAPHORE = asyncio.Semaphore(2)


def file_ext(filename: str | None) -> str:
    return Path(filename or "").suffix.lower().lstrip(".")


def check_office_magic(ext: str, data: bytes) -> None:
    if not data.startswith(_OFFICE_MAGIC.get(ext, ())):
        raise InstanceProcessingException(
            f"Fayl .{ext} formatiga mos emas yoki buzilgan"
        )


# ---------------------------------------------------------------------------
# Rasm -> PDF
# ---------------------------------------------------------------------------
def _normalize_image(data: bytes) -> tuple[bytes, int, int]:
    """Rasmni ochadi, telefondagi EXIF burilishini to'g'rilaydi va pymupdf
    to'g'ridan-to'g'ri joylay oladigan (PNG/JPEG) ko'rinishga keltiradi."""
    try:
        img = Image.open(io.BytesIO(data))
        if img.width * img.height > _MAX_IMAGE_PIXELS:
            raise InstanceProcessingException("Rasm o'lchami juda katta")
        fmt = img.format
        # EXIF Orientation (0x0112): 1 — burilmagan. Telefon rasmlarida ko'pincha 6/8.
        oriented = img.getexif().get(0x0112, 1) not in (0, 1)
        # JPEG/PNG burilmagan bo'lsa — qayta siqilmaydi (sifat yo'qolmaydi)
        if fmt in ("JPEG", "PNG") and not oriented:
            return data, img.width, img.height
        rotated = ImageOps.exif_transpose(img)
    except InstanceProcessingException:
        raise
    except Exception as exc:
        raise InstanceProcessingException("Rasmni o'qib bo'lmadi yoki fayl buzilgan") from exc

    out = io.BytesIO()
    if rotated.mode in ("RGBA", "LA", "P"):
        rotated.convert("RGBA").save(out, "PNG")
    else:
        rotated.convert("RGB").save(out, "JPEG", quality=92)
    return out.getvalue(), rotated.width, rotated.height


def _fit_rect(page_rect: pymupdf.Rect, w: int, h: int) -> pymupdf.Rect:
    """Rasmni chekkalar ichiga proporsiyasini saqlab, markazga joylaydigan
    to'rtburchak. `keep_proportion=True` ga tayanilmaydi: shaffof (alfa
    kanalli) PNG'da pymupdf rasmni butun maydonga cho'zib yuborardi."""
    box = page_rect + (_MARGIN, _MARGIN, -_MARGIN, -_MARGIN)
    scale = min(box.width / w, box.height / h)
    fw, fh = w * scale, h * scale
    x0 = box.x0 + (box.width - fw) / 2
    y0 = box.y0 + (box.height - fh) / 2
    return pymupdf.Rect(x0, y0, x0 + fw, y0 + fh)


def images_to_pdf(images: list[bytes]) -> bytes:
    """Rasmlar ro'yxatini bitta PDF'ga yig'adi — har rasm alohida A4 sahifada."""
    doc = pymupdf.open()
    try:
        for data in images:
            stream, w, h = _normalize_image(data)
            # Keng rasm — albom (landscape) sahifa
            page_rect = (
                pymupdf.Rect(0, 0, _A4.height, _A4.width) if w > h else _A4
            )
            page = doc.new_page(width=page_rect.width, height=page_rect.height)
            page.insert_image(_fit_rect(page_rect, w, h), stream=stream, keep_proportion=False)
        return doc.tobytes(garbage=3, deflate=True)
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# Ofis hujjati -> PDF (LibreOffice)
# ---------------------------------------------------------------------------
def _soffice_bin() -> str:
    path = shutil.which("soffice") or shutil.which("libreoffice")
    if not path:
        # Lokal (Docker'siz) muhitda LibreOffice bo'lmasligi mumkin
        raise InfrastructureException("Konvertor (LibreOffice) serverda o'rnatilmagan")
    return path


async def office_to_pdf(data: bytes, ext: str, timeout: int) -> bytes:
    """Word/Excel/PowerPoint hujjatini LibreOffice orqali PDF'ga o'giradi."""
    check_office_magic(ext, data)
    soffice = _soffice_bin()

    async with _OFFICE_SEMAPHORE:
        with tempfile.TemporaryDirectory(prefix="turon_convert_") as tmp:
            workdir = Path(tmp)
            src = workdir / f"input.{ext}"
            src.write_bytes(data)
            # Har jarayonga ALOHIDA profil papkasi: bitta umumiy profil bilan
            # parallel ikkinchi soffice "profil band" deb darhol chiqib ketadi.
            profile = workdir / f"profile_{uuid.uuid4().hex}"
            proc = await asyncio.create_subprocess_exec(
                soffice,
                "--headless", "--norestore", "--nolockcheck", "--nodefault",
                f"-env:UserInstallation={profile.as_uri()}",
                "--convert-to", "pdf",
                "--outdir", str(workdir),
                str(src),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except TimeoutError:
                proc.kill()
                await proc.wait()
                logger.warning("[Convert] LibreOffice %ss da tugamadi (.%s)", timeout, ext)
                raise InstanceProcessingException(
                    "Hujjat juda murakkab — o'girish vaqti tugadi"
                ) from None

            out = workdir / "input.pdf"
            if proc.returncode != 0 or not out.exists():
                logger.error(
                    "[Convert] LibreOffice xatosi (.%s, kod %s): %s",
                    ext, proc.returncode, stderr.decode(errors="ignore")[-500:],
                )
                raise InstanceProcessingException(
                    "Hujjatni PDF'ga o'girib bo'lmadi — fayl buzilgan yoki parol bilan himoyalangan"
                )
            return out.read_bytes()
