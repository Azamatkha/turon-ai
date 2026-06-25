"""
1-QADAM: Skannerlangan PDF dan matn ajratib olish.

Skaner PDF ichida MATN yo'q, RASM bor. Shuning uchun yo'l:
    PDF --(poppler/pdf2image)--> rasm --(TOZALASH)--> tesseract --> matn

OCR sifatini oshirish uchun har bir sahifa rasmini OLDIN tozalaymiz:
    1) kulrang (grayscale) qilamiz
    2) kontrastni avtomatik kuchaytiramiz
    3) Otsu usuli bilan oq-qora (binar) qilamiz -- harflar aniq ajraladi

Test qilish (backend papkasida):
    python -m app.rag.ocr data/documents/test.pdf
"""
from pdf2image import convert_from_path
from PIL import Image, ImageOps, ImageFilter
import pytesseract

# ====== WINDOWS SOZLAMASI ======
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = None  # masalan: r"C:\poppler\Library\bin"

TILLAR = "uzb+rus"          # o'zbek (lotin) + rus. Kirill hujjat bo'lsa: "uzb_cyrl+rus"
DPI = 400                   # yuqoriroq DPI = mayda matn aniqroq (sekinroq)
TESS_CONFIG = "--oem 1 --psm 3"   # LSTM dvigatel + sahifa tuzilishini avtomatik aniqlash


def _otsu_chegara(kulrang: Image.Image) -> int:
    """Rasm uchun eng yaxshi oq/qora ajratish chegarasini (Otsu) hisoblaydi."""
    hist = kulrang.histogram()[:256]
    jami = sum(hist)
    sum_jami = sum(i * h for i, h in enumerate(hist))
    sumB = 0.0
    wB = 0
    maksimum = 0.0
    chegara = 127
    for i in range(256):
        wB += hist[i]
        if wB == 0:
            continue
        wF = jami - wB
        if wF == 0:
            break
        sumB += i * hist[i]
        mB = sumB / wB
        mF = (sum_jami - sumB) / wF
        oraliq = wB * wF * (mB - mF) ** 2
        if oraliq > maksimum:
            maksimum = oraliq
            chegara = i
    return chegara


def _rasmni_tayyorla(rasm: Image.Image) -> Image.Image:
    """OCR oldidan rasmni tozalaydi: kulrang + kontrast + oq-qora."""
    kulrang = rasm.convert("L")
    kulrang = ImageOps.autocontrast(kulrang)
    kulrang = kulrang.filter(ImageFilter.MedianFilter(size=3))  # mayda shovqinni o'chiradi
    t = _otsu_chegara(kulrang)
    return kulrang.point(lambda p: 255 if p > t else 0, mode="1")


def pdf_dan_sahifalar(pdf_yoli: str) -> list[str]:
    """Bitta PDF'ni HAR BIR SAHIFA matni alohida bo'lgan ro'yxat qilib qaytaradi."""
    sahifalar = convert_from_path(pdf_yoli, dpi=DPI, poppler_path=POPPLER_PATH)
    natija = []
    for i, sahifa in enumerate(sahifalar, start=1):
        toza = _rasmni_tayyorla(sahifa)
        matn = pytesseract.image_to_string(toza, lang=TILLAR, config=TESS_CONFIG)
        natija.append(matn)
        print(f"  {i}-sahifa o'qildi ({len(matn)} belgi)")
    return natija


def pdf_dan_matn(pdf_yoli: str) -> str:
    """Bitta PDF'dagi barcha sahifani BITTA matnga birlashtirib qaytaradi."""
    return "\n".join(pdf_dan_sahifalar(pdf_yoli))


if __name__ == "__main__":
    import sys
    yol = sys.argv[1] if len(sys.argv) > 1 else "data/documents/test.pdf"
    print(f"O'qilyapti: {yol}")
    natija = pdf_dan_matn(yol)
    print("\n===== AJRATILGAN MATN (boshi) =====")
    print(natija[:1500])
    print(f"\n----- JAMI: {len(natija)} belgi -----")
