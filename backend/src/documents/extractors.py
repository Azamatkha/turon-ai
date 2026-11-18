"""Foydalanuvchi yuborgan hujjatdan matn ajratish (hujjat tahlilchisi uchun).

Qo'llanadigan turlar:
* PDF — matn qatlami bor sahifa to'g'ridan-to'g'ri o'qiladi; SKAN sahifa
  Qwen (vision) ga rasm qilib beriladi. Tesseract faqat zaxira: model rasmni
  qabul qilmasa yoki sahifada yiqilsa. Tesseract skanerlangan ichki
  hujjatlarni (muhr, imzo, kirill-lotin aralash) yomon o'qiydi.
* Word (.docx) — zip ichidagi `word/document.xml` dan (yangi paket kerak emas).
* Excel (.xlsx) — openpyxl, har varaq jadval ko'rinishida.
* Eski/boshqa ofis turlari (.doc, .xls, .ppt, .pptx, .odt, .ods, .odp, .rtf) —
  LibreOffice bilan PDF'ga o'girilib, PDF yo'lidan o'tadi.
* Rasm (telefonda suratga olingan hujjat) — Qwen vision, zaxira Tesseract.
* .txt / .csv — oddiy matn.

MAXFIYLIK: fayl diskka yozilmaydi (faqat LibreOffice uchun vaqtinchalik
papkaga, keyin darhol o'chiriladi) va bilim bazasiga TUSHMAYDI.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import io
import re
from xml.etree import ElementTree
import zipfile

from anyio import to_thread

from loggers import get_logger
from src.core.ai.interfaces import BaseAIClient
from src.core.errors.exceptions import InstanceProcessingException
from src.knowledge.pdf_extractor import (
    _normalize,
    _strip_noise_lines,
    join_pages,
    ocr_png,
    split_pdf_pages,
)
from src.knowledge.prompts import PDF_VISION_SYSTEM

logger = get_logger(__name__)

PDF_EXTS = {"pdf"}
DOCX_EXTS = {"docx"}
XLSX_EXTS = {"xlsx"}
# LibreOffice orqali PDF'ga o'giriladiganlar
CONVERT_EXTS = {"doc", "odt", "rtf", "xls", "ods", "ppt", "pptx", "odp"}
IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff", "heic", "heif"}
TEXT_EXTS = {"txt", "csv"}
SUPPORTED_EXTS = PDF_EXTS | DOCX_EXTS | XLSX_EXTS | CONVERT_EXTS | IMAGE_EXTS | TEXT_EXTS

# Ko'pi bilan shuncha sahifa o'qiladi (matnli sahifalar arzon)
MAX_PDF_PAGES = 120
# Skan sahifalar Qwen'ga beriladi — har biri ~10-40 soniya. Ko'proq bo'lsa,
# javob kutish juda uzoq bo'ladi; qolganlari "o'qilmadi" deb aytiladi.
MAX_SCAN_PAGES = 15
# Bir vaqtda modelga yuboriladigan sahifalar (server boshqa chatlar bilan band)
VISION_CONCURRENCY = 2
VISION_PAGE_MAX_TOKENS = 4096
VISION_PAGE_TIMEOUT = 180.0
# Excel: bitta varaqdan ko'pi bilan shuncha qator
MAX_SHEET_ROWS = 400
# Zip ichidagi XML "bomba"sidan himoya (ochilgan hajm)
_MAX_XML_BYTES = 40 * 1024 * 1024
# Rasm modelga berilishidan oldin shu o'lchamgacha kichraytiriladi
_MAX_IMAGE_SIDE = 2200

_ZIP_MAGIC = b"PK\x03\x04"

# Bosqich xabari: (qadam, bajarilgani, jami) — SSE "status" hodisasiga aylanadi
Progress = Callable[[int, int], Awaitable[None]]


@dataclass(slots=True)
class ExtractedDocument:
    text: str
    kind: str              # "pdf" | "docx" | "xlsx" | "image" | "text" | ...
    pages: int = 0         # PDF sahifalari (boshqa turlarda 0)
    vision_pages: int = 0  # Qwen o'qigan skan sahifalar
    ocr_pages: int = 0     # Tesseract (zaxira) o'qigan sahifalar
    skipped_pages: int = 0  # chegaradan oshgani uchun o'qilmagan sahifalar


def file_ext(filename: str | None) -> str:
    name = (filename or "").strip().lower()
    return name.rsplit(".", 1)[-1] if "." in name else ""


# ---------------------------------------------------------------------------
# Rasm (skan sahifa / foto) -> matn
# ---------------------------------------------------------------------------
async def _read_scan(
    png: bytes, ai_client: BaseAIClient, use_vision: bool
) -> tuple[str, bool]:
    """Bitta rasmni o'qiydi. Qaytaradi: (matn, model_o'qidimi)."""
    if use_vision:
        try:
            res = await ai_client.read_image(
                png,
                prompt="Transcribe this page.",
                system_prompt=PDF_VISION_SYSTEM,
                max_tokens=VISION_PAGE_MAX_TOKENS,
                timeout=VISION_PAGE_TIMEOUT,
            )
            return res.text.strip(), True
        except Exception as exc:  # noqa: BLE001 - zaxira yo'lga o'tamiz
            logger.warning("[Doc] Sahifani model o'qiy olmadi (%s) — OCR", type(exc).__name__)
    try:
        text = await to_thread.run_sync(ocr_png, png)
    except InstanceProcessingException:
        return "", False
    return _strip_noise_lines(text).strip(), False


async def _read_pdf(
    data: bytes, ai_client: BaseAIClient, progress: Progress | None
) -> ExtractedDocument:
    pages, total, skipped = await to_thread.run_sync(
        lambda: split_pdf_pages(data, max_pages=MAX_PDF_PAGES, max_scans=MAX_SCAN_PAGES)
    )
    scan_idx = [i for i, p in enumerate(pages) if p.png is not None]
    parts = [_strip_noise_lines(p.text).strip() if p.png is None else "" for p in pages]
    vision = ocr = 0
    if scan_idx:
        use_vision = await ai_client.supports_vision()
        sem = asyncio.Semaphore(VISION_CONCURRENCY)
        done = 0

        async def one(i: int) -> None:
            nonlocal done, vision, ocr
            async with sem:
                png = pages[i].png
                assert png is not None
                text, by_model = await _read_scan(png, ai_client, use_vision)
            parts[i] = text
            if by_model:
                vision += 1
            else:
                ocr += 1
            done += 1
            if progress is not None:
                await progress(done, len(scan_idx))

        if progress is not None:
            await progress(0, len(scan_idx))
        await asyncio.gather(*(one(i) for i in scan_idx))
    return ExtractedDocument(
        text=join_pages(parts),
        kind="pdf",
        pages=total,
        vision_pages=vision,
        ocr_pages=ocr,
        skipped_pages=skipped,
    )


def _prepare_image(data: bytes) -> bytes:
    """Rasmni ochadi (iPhone HEIC ham), EXIF burilishini to'g'rilaydi va
    modelga mos PNG'ga aylantiradi."""
    try:
        from PIL import Image, ImageOps
        from pillow_heif import register_heif_opener

        register_heif_opener()
        src = Image.open(io.BytesIO(data))
        if src.width * src.height > 60_000_000:
            raise InstanceProcessingException("Rasm o'lchami juda katta")
        img = ImageOps.exif_transpose(src).convert("RGB")
        img.thumbnail((_MAX_IMAGE_SIDE, _MAX_IMAGE_SIDE))
        out = io.BytesIO()
        img.save(out, "PNG")
        return out.getvalue()
    except InstanceProcessingException:
        raise
    except Exception as exc:
        raise InstanceProcessingException("Rasmni o'qib bo'lmadi yoki fayl buzilgan") from exc


async def _read_image(
    data: bytes, ai_client: BaseAIClient, progress: Progress | None
) -> ExtractedDocument:
    png = await to_thread.run_sync(_prepare_image, data)
    if progress is not None:
        await progress(0, 1)
    use_vision = await ai_client.supports_vision()
    text, by_model = await _read_scan(png, ai_client, use_vision)
    if progress is not None:
        await progress(1, 1)
    return ExtractedDocument(
        text=_normalize(text),
        kind="image",
        pages=1,
        vision_pages=int(by_model),
        ocr_pages=int(not by_model),
    )


# ---------------------------------------------------------------------------
# Word (.docx)
# ---------------------------------------------------------------------------
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _read_zip_xml(zf: zipfile.ZipFile, name: str) -> bytes | None:
    try:
        info = zf.getinfo(name)
    except KeyError:
        return None
    if info.file_size > _MAX_XML_BYTES:
        raise InstanceProcessingException("Hujjat juda katta yoki buzilgan")
    return zf.read(info)


def _docx_paragraph(p: ElementTree.Element) -> str:
    out: list[str] = []
    for node in p.iter():
        if node.tag == _W + "t" and node.text:
            out.append(node.text)
        elif node.tag == _W + "tab":
            out.append("\t")
        elif node.tag in (_W + "br", _W + "cr"):
            out.append("\n")
    return "".join(out).strip()


def _docx_table(tbl: ElementTree.Element) -> str:
    rows: list[str] = []
    for tr in tbl.iter(_W + "tr"):
        cells = []
        for tc in tr.findall(_W + "tc"):
            cell = " ".join(
                t for t in (_docx_paragraph(p) for p in tc.iter(_W + "p")) if t
            )
            cells.append(cell.replace("|", "/").replace("\n", " "))
        if any(cells):
            rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


def docx_to_text(data: bytes) -> str:
    """.docx matnini (paragraflar + jadvallar) tartib bilan ajratadi."""
    if not data.startswith(_ZIP_MAGIC):
        raise InstanceProcessingException("Fayl .docx formatiga mos emas yoki buzilgan")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            raw = _read_zip_xml(zf, "word/document.xml")
            if raw is None:
                raise InstanceProcessingException("Fayl .docx formatiga mos emas")
            root = ElementTree.fromstring(raw)
    except InstanceProcessingException:
        raise
    except (zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise InstanceProcessingException("Word hujjatini o'qib bo'lmadi — fayl buzilgan") from exc

    body = root.find(_W + "body")
    if body is None:
        return ""
    blocks: list[str] = []
    for child in body:
        if child.tag == _W + "p":
            text = _docx_paragraph(child)
        elif child.tag == _W + "tbl":
            text = _docx_table(child)
        else:
            continue
        if text:
            blocks.append(text)
    return _normalize("\n".join(blocks))


# ---------------------------------------------------------------------------
# Excel (.xlsx)
# ---------------------------------------------------------------------------
def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip().replace("\n", " ").replace("|", "/")


def xlsx_to_text(data: bytes) -> str:
    """Har varaq: nomi + jadval qatorlari (bo'sh qator/ustunlarsiz)."""
    if not data.startswith(_ZIP_MAGIC):
        raise InstanceProcessingException("Fayl .xlsx formatiga mos emas yoki buzilgan")
    try:
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:
        raise InstanceProcessingException("Excel faylini o'qib bo'lmadi — fayl buzilgan") from exc

    sheets: list[str] = []
    try:
        for ws in wb.worksheets:
            rows: list[str] = []
            extra = 0
            for row in ws.iter_rows(values_only=True):
                cells = [_cell(v) for v in row]
                while cells and not cells[-1]:
                    cells.pop()
                if not any(cells):
                    continue
                if len(rows) >= MAX_SHEET_ROWS:
                    extra += 1
                    continue
                rows.append("| " + " | ".join(cells) + " |")
            if not rows:
                continue
            block = f"### Varaq: {ws.title}\n" + "\n".join(rows)
            if extra:
                block += f"\n(... yana {extra} qator ko'rsatilmadi)"
            sheets.append(block)
    finally:
        wb.close()
    return "\n\n".join(sheets)


# ---------------------------------------------------------------------------
# Oddiy matn
# ---------------------------------------------------------------------------
def plain_to_text(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1251"):
        try:
            return _normalize(data.decode(enc))
        except UnicodeDecodeError:
            continue
    return _normalize(data.decode("utf-8", "replace"))


_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


async def extract_document(
    data: bytes,
    filename: str,
    ai_client: BaseAIClient,
    *,
    convert_timeout: int,
    progress: Progress | None = None,
) -> ExtractedDocument:
    """Fayl turiga qarab matn ajratadi. Qo'llanmaydigan tur yoki bo'sh
    natija — InstanceProcessingException (foydalanuvchiga tushunarli matn)."""
    ext = file_ext(filename)
    if not data:
        raise InstanceProcessingException("Fayl bo'sh")
    if ext not in SUPPORTED_EXTS:
        raise InstanceProcessingException(
            "Bu fayl turi qo'llanmaydi. PDF, Word, Excel, PowerPoint, rasm yoki "
            "matn faylini yuboring."
        )

    if ext in PDF_EXTS:
        doc = await _read_pdf(data, ai_client, progress)
    elif ext in DOCX_EXTS:
        doc = ExtractedDocument(text=await to_thread.run_sync(docx_to_text, data), kind="docx")
    elif ext in XLSX_EXTS:
        doc = ExtractedDocument(text=await to_thread.run_sync(xlsx_to_text, data), kind="xlsx")
    elif ext in TEXT_EXTS:
        doc = ExtractedDocument(text=plain_to_text(data), kind="text")
    elif ext in IMAGE_EXTS:
        doc = await _read_image(data, ai_client, progress)
    else:
        from src.tools.pdf_convert import office_to_pdf

        pdf = await office_to_pdf(data, ext, timeout=convert_timeout)
        doc = await _read_pdf(pdf, ai_client, progress)
        doc.kind = ext

    doc.text = _CONTROL_RE.sub("", doc.text).strip()
    if not doc.text:
        raise InstanceProcessingException(
            "Hujjatdan matn ajratib bo'lmadi — fayl bo'sh, parol bilan himoyalangan "
            "yoki skan sifati juda past."
        )
    return doc
