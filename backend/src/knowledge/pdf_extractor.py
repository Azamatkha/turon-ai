"""Extract plain text from a PDF, falling back to OCR for scanned pages.

Two-stage on purpose:

1. PyMuPDF reads the page's *text layer*. Digitally produced PDFs (Word ->
   PDF) carry one, and reading it is instant and lossless.
2. Only when a page has (almost) no text layer — i.e. it is a scan — the page
   is rasterised and pushed through Tesseract. OCR is slow, so we never run it
   on pages that do not need it.

Scanned internal documents are full of hand-written signatures, stamps and
dotted signature lines. Tesseract cannot read handwriting and emits short
garbage lines for those areas; `_strip_noise_lines` drops the obvious ones and
the LLM clean-up stage (see UploadPdfUseCase) removes the rest.

Both third-party imports are done lazily inside the functions so the app still
boots (and every other endpoint keeps working) when the OCR stack is not
installed in the image yet — the failure then surfaces as a clear error on this
endpoint only.
"""

import re
from typing import Any

from src.core.errors.exceptions import InstanceProcessingException

# Sahifada shundan kam "haqiqiy" belgi bo'lsa — matn qatlami yo'q deb hisoblab,
# sahifani OCR'ga yuboramiz. Skanerlangan sahifada ham ba'zan bir-ikki belgi
# (kolontitul, sahifa raqami) topiladi, shuning uchun nol emas.
MIN_TEXT_CHARS_PER_PAGE = 60

# OCR uchun rasm zichligi. 300 DPI — bosma matn uchun Tesseract tavsiyasi;
# pastroqda harflar chalkashadi, balandroqda esa faqat sekinlashadi.
OCR_DPI = 300

# Tesseract til paketlari: o'zbek (lotin + kirill) va rus. Hujjatlar shu
# tillarda; ingliz qo'shimcha (raqam/lotin qisqartmalar uchun).
OCR_LANGS = "uzb+uzb_cyrl+rus+eng"


# Imzo/muhr joylaridan qoladigan shovqin. OCR qo'lda yozilgan joyni o'qiy
# olmaydi va o'rniga qisqa, ma'nosiz "so'z"lar yoki chiziqlar qaytaradi.
_UNDERLINE_RE = re.compile(r"^[\s_\-–—.…]{3,}$")
_WORD_RE = re.compile(r"[0-9a-zA-Zа-яёА-ЯЁўқғҳЎҚҒҲ'’]+")


def _is_noise_line(line: str) -> bool:
    """Qator imzo/muhr qoldig'imi (mazmunsiz OCR chiqindisi)."""
    s = line.strip()
    if not s:
        return False
    # "______", "-----", "......" — imzo/to'ldirish chiziqlari
    if _UNDERLINE_RE.match(s):
        return True
    words = _WORD_RE.findall(s)
    if not words:
        # Umuman harf/raqam yo'q — faqat tinish belgilari qolgan
        return True
    letters = sum(len(w) for w in words)
    # Qatorning yarmidan ko'pi begona belgi bo'lsa — bu matn emas, shovqin
    if letters / len(s) < 0.5:
        return True
    # Qisqa qator, unda ham faqat 1-2 harfli parchalar — qo'lyozma qoldig'i
    return len(s) <= 12 and max(len(w) for w in words) <= 2


def _strip_noise_lines(text: str) -> str:
    kept = [ln for ln in text.split("\n") if not _is_noise_line(ln)]
    return "\n".join(kept)


_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def _normalize(text: str) -> str:
    lines = [_MULTI_SPACE_RE.sub(" ", ln.strip()) for ln in text.split("\n")]
    return _MULTI_BLANK_RE.sub("\n\n", "\n".join(lines)).strip()


def _ocr_page(page: Any) -> str:
    """Bitta sahifani rasmga o'girib, Tesseract orqali o'qiydi."""
    try:
        import io

        from PIL import Image
        import pytesseract
    except ImportError as exc:  # pragma: no cover - muhitga bog'liq
        raise InstanceProcessingException(
            "OCR uchun kutubxonalar o'rnatilmagan (pytesseract, Pillow). "
            "Bu PDF skanerlangan — matn qatlami yo'q."
        ) from exc

    pixmap = page.get_pixmap(dpi=OCR_DPI)
    image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    try:
        return str(pytesseract.image_to_string(image, lang=OCR_LANGS))
    except Exception as exc:
        raise InstanceProcessingException(
            f"OCR (Tesseract) ishlamadi: {type(exc).__name__}: {exc!r}. "
            "Docker image'da tesseract-ocr va til paketlari bormi?"
        ) from exc


def extract_pdf_text(file_bytes: bytes) -> tuple[str, int, int]:
    """PDF baytlaridan matn ajratadi.

    Qaytaradi: (matn, sahifalar_soni, ocr_qilingan_sahifalar_soni)."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover - muhitga bog'liq
        raise InstanceProcessingException(
            "PDF o'qish kutubxonasi (PyMuPDF) o'rnatilmagan."
        ) from exc

    try:
        document = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise InstanceProcessingException(
            f"PDF ochilmadi (buzilgan yoki parol bilan himoyalangan?): "
            f"{type(exc).__name__}: {exc!r}"
        ) from exc

    parts: list[str] = []
    ocr_pages = 0
    try:
        for page in document:
            text = str(page.get_text("text") or "")
            if len(text.strip()) < MIN_TEXT_CHARS_PER_PAGE:
                # Skanerlangan sahifa — OCR
                text = _ocr_page(page)
                ocr_pages += 1
            cleaned = _strip_noise_lines(text)
            if cleaned.strip():
                parts.append(cleaned.strip())
        page_count = document.page_count
    finally:
        document.close()

    return _normalize("\n\n".join(parts)), page_count, ocr_pages
