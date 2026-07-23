"""Read a page image with an Ollama vision model (e.g. qwen3-vl).

Ollama's native /api/chat accepts images: each message may carry an `images`
list of base64-encoded PNG/JPEG. The vision model then "sees" the page and can
transcribe printed text, stamps and even hand-written notes that Tesseract
cannot read.

Kept separate from the OllamaClient singleton so it is easy to try/compare
against Tesseract without touching the working RAG pipeline.
"""

import base64
import time

import httpx

from src.core.errors.exceptions import InfrastructureException
from src.main.config import config

# Model'ga aniq vazifa: KO'RGANINI o'qi, o'zingdan QO'SHMA. Bu muhim — vision
# modellar o'qiy olmagan joyni "mantiqan mos" so'z bilan to'ldirib yuborishga
# moyil; bank hujjatida bu raqam/sanani buzib qo'yishi mumkin.
VISION_OCR_PROMPT = (
    "Bu skanerlangan hujjat sahifasining rasmi. Undagi BARCHA matnni "
    "o'qiganingdek, aynan ko'chirib yoz.\n"
    "- Sahifada nima yozilgan bo'lsa, o'sha alifboda (kirill yoki lotin) yoz.\n"
    "- O'zingdan hech narsa QO'SHMA, to'ldirma yoki tarjima qilma.\n"
    "- O'qib bo'lmagan joyni [o'qib bo'lmadi] deb belgila, taxmin qilma.\n"
    "- Muhr, imzo va qo'lda yozilgan joylarni ham iloji boricha o'qishga urin.\n"
    "- Faqat matnning o'zini qaytar, izoh berma."
)


async def vision_ocr_png(png_bytes: bytes, *, timeout: int = 300) -> str:
    """Bitta sahifa rasmini (PNG baytlari) vision modelga berib, matnini
    qaytaradi. Sekin — sahifa uchun bir necha o'n soniya ketishi mumkin."""
    base_url = config.ai.OLLAMA_BASE_URL.rstrip("/")
    if not base_url:
        raise InfrastructureException(
            "OLLAMA_BASE_URL sozlanmagan — vision model chaqirib bo'lmaydi."
        )

    image_b64 = base64.b64encode(png_bytes).decode("ascii")
    payload = {
        "model": config.ai.OLLAMA_VISION_MODEL,
        "messages": [
            {"role": "user", "content": VISION_OCR_PROMPT, "images": [image_b64]}
        ],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.1,
            # Butun sahifa matni sig'ishi uchun keng
            "num_predict": 4096,
            "num_ctx": config.ai.OLLAMA_NUM_CTX,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{base_url}/api/chat", json=payload)
    except httpx.HTTPError as exc:
        raise InfrastructureException(
            f"Vision model (Ollama) bilan bog'lanib bo'lmadi: {exc}"
        ) from exc

    if resp.status_code != 200:
        raise InfrastructureException(
            f"Vision model xatosi {resp.status_code}: {resp.text[:200]}. "
            f"'{config.ai.OLLAMA_VISION_MODEL}' modeli Ollama'da bormi "
            "(ollama list)?"
        )
    data = resp.json()
    return str((data.get("message") or {}).get("content", "")).strip()


async def vision_ocr_timed(png_bytes: bytes) -> tuple[str, int]:
    """vision_ocr_png bilan bir xil, lekin (matn, ketgan_millisekund) qaytaradi
    — diagnostikada tezlikni solishtirish uchun."""
    start = time.monotonic()
    text = await vision_ocr_png(png_bytes)
    elapsed_ms = int((time.monotonic() - start) * 1000)
    return text, elapsed_ms
