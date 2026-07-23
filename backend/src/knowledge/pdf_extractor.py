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

# Tesseract til paketlari SAHIFA ALIFBOSIGA qarab tanlanadi. Lotin va kirillni
# bir chaqiruvda berish MUMKIN EMAS: Tesseract har harfni to'rt alifbodan
# aralash tanlab, "фаoliяти", "АКТIVЛАР", "TENГЛАШТИРИЛГАН" kabi buzuq so'zlar
# chiqaradi. Shuning uchun avval sahifa alifbosi aniqlanadi (image_to_osd),
# so'ng faqat o'sha alifbo modellari beriladi.
OCR_LANGS_CYRILLIC = "uzb_cyrl+rus"
OCR_LANGS_LATIN = "uzb+eng"
# Alifboni aniqlab bo'lmaganda (juda kam matnli sahifa) — zaxira variant.
OCR_LANGS_FALLBACK = OCR_LANGS_LATIN


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


def _norm_key(line: str) -> str:
    """Qatorni taqqoslash uchun kalitga aylantiradi. OCR har sahifada bir xil
    kolontitulni bir oz boshqacha o'qiydi ("мониторин" / "мониторинг"), shuning
    uchun harflarni kichik qilib, bo'sh joy va tinishni tashlaymiz va boshidagi
    bir bo'lakni olamiz.

    Kalit ATAYIN qisqa (20 belgi): OCR bir sahifada "тижорат", boshqasida
    "тиждорат" deb o'qishi mumkin, uzun kalitda esa bu ikkisi boshqa-boshqa
    qator bo'lib sanalib, kolontitul aniqlanmay qolardi."""
    return "".join(_WORD_RE.findall(line.lower()))[:20]


# Kolontitul deb hisoblash uchun qator kamida shuncha sahifada uchrashi kerak.
_RUNNING_MIN_PAGES = 3
# Va sahifalarning kamida shuncha ulushida.
_RUNNING_MIN_RATIO = 0.4


def _strip_running_headers(pages: list[str]) -> list[str]:
    """Har sahifada takrorlanadigan kolontitul/futer qatorlarini olib tashlaydi.

    Ichki hujjatlarda har sahifa tepasida hujjatning to'liq nomi turadi. OCR uni
    har sahifada qayta o'qiydi va matn oqimiga qo'shib yuboradi — natijada bitta
    va o'sha jumla har bo'lakning o'rtasida takrorlanib, bazani ifloslantiradi
    va qidiruvni chalg'itadi."""
    if len(pages) < _RUNNING_MIN_PAGES:
        return pages

    counts: dict[str, int] = {}
    for page in pages:
        # Bir sahifadagi takrorlar bir marta sanaladi
        for key in {_norm_key(ln) for ln in page.split("\n") if len(ln.strip()) >= 12}:
            counts[key] = counts.get(key, 0) + 1

    threshold = max(_RUNNING_MIN_PAGES, int(len(pages) * _RUNNING_MIN_RATIO))
    running = {k for k, c in counts.items() if c >= threshold}
    if not running:
        return pages
    return [
        "\n".join(ln for ln in page.split("\n") if _norm_key(ln) not in running)
        for page in pages
    ]


_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def _normalize(text: str) -> str:
    lines = [_MULTI_SPACE_RE.sub(" ", ln.strip()) for ln in text.split("\n")]
    return _MULTI_BLANK_RE.sub("\n\n", "\n".join(lines)).strip()


def _detect_langs(image: Any, pytesseract: Any) -> str:
    """Sahifa qaysi alifboda yozilganini aniqlab, mos til to'plamini qaytaradi.

    image_to_osd Tesseract'ning tayyor skript-aniqlagichi ("Script: Cyrillic").
    Matn kam bo'lgan sahifada u xato beradi — bunda zaxira to'plamga qaytamiz."""
    try:
        osd = str(pytesseract.image_to_osd(image))
    except Exception:
        return OCR_LANGS_FALLBACK
    for line in osd.split("\n"):
        if line.lower().startswith("script:"):
            script = line.split(":", 1)[1].strip().lower()
            if "cyrillic" in script:
                return OCR_LANGS_CYRILLIC
            if "latin" in script:
                return OCR_LANGS_LATIN
    return OCR_LANGS_FALLBACK


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
    # Kulrangga o'tkazamiz — skanerdagi rangli shovqin (muhr siyohi, qog'oz
    # tusi) harf tanishga xalaqit bermasin.
    image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("L")
    langs = _detect_langs(image, pytesseract)
    try:
        return str(pytesseract.image_to_string(image, lang=langs))
    except Exception as exc:
        raise InstanceProcessingException(
            f"OCR (Tesseract) ishlamadi: {type(exc).__name__}: {exc!r}. "
            "Docker image'da tesseract-ocr va til paketlari bormi?"
        ) from exc


def render_page_png(file_bytes: bytes, page_index: int, dpi: int = OCR_DPI) -> bytes:
    """Bitta sahifani PNG rasm (baytlar) qilib qaytaradi — vision modelga yoki
    diagnostikaga berish uchun."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover - muhitga bog'liq
        raise InstanceProcessingException(
            "PDF o'qish kutubxonasi (PyMuPDF) o'rnatilmagan."
        ) from exc

    document = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        if page_index < 0 or page_index >= document.page_count:
            raise InstanceProcessingException(
                f"Sahifa {page_index} yo'q — hujjatda {document.page_count} sahifa bor."
            )
        pixmap = document[page_index].get_pixmap(dpi=dpi)
        return bytes(pixmap.tobytes("png"))
    finally:
        document.close()


def extract_single_page(file_bytes: bytes, page_index: int) -> tuple[str, str]:
    """Bitta sahifani ikki usulda o'qiydi (diagnostika uchun):
    (matn_qatlami, tesseract_ocr). Har biri bo'sh bo'lishi mumkin."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover - muhitga bog'liq
        raise InstanceProcessingException(
            "PDF o'qish kutubxonasi (PyMuPDF) o'rnatilmagan."
        ) from exc

    document = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        if page_index < 0 or page_index >= document.page_count:
            raise InstanceProcessingException(
                f"Sahifa {page_index} yo'q — hujjatda {document.page_count} sahifa bor."
            )
        page = document[page_index]
        text_layer = str(page.get_text("text") or "").strip()
        ocr_text = _strip_noise_lines(_ocr_page(page)).strip()
        return text_layer, ocr_text
    finally:
        document.close()


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
            parts.append(_strip_noise_lines(text).strip())
        page_count = document.page_count
    finally:
        document.close()

    # Kolontitul faqat BARCHA sahifalar yig'ilgach aniqlanadi (qaysi qator
    # takrorlanayotganini bitta sahifadan bilib bo'lmaydi).
    pages = [p for p in _strip_running_headers(parts) if p.strip()]
    return _normalize("\n\n".join(pages)), page_count, ocr_pages
