"""Bazadagi hujjatlardan sinov savollarini tuzish.

Savollar BIR MARTA tuziladi va saqlanadi: keyingi o'lchovlar aynan shu
savollar bilan qilinadi, aks holda "avval/endi" foizlari solishtirib
bo'lmaydi (har safar boshqa savol — boshqa qiyinlik).
"""

from typing import Any

from loggers import get_logger
from src.core.ai.interfaces import BaseAIClient
from src.core.utils.uzbek_script import to_cyrillic
from src.evaluation.schemas import EvalCase

logger = get_logger(__name__)

# Model ko'radigan hujjat hajmi — savol va faktlar shu bo'lakdan olinadi
GEN_DOC_CHARS = 6000
GEN_TIMEOUT_SECONDS = 120.0
GEN_MAX_TOKENS = 1500

# Model tuzadigan uslublar. "cyrillic" model yozmaydi — "colloquial"
# savol kod bilan kirillga o'giriladi (model kirill imlosida adashadi).
_MODEL_STYLES = ("formal", "colloquial", "typo", "detail", "russian", "absent")

GEN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "style": {"type": "string", "enum": list(_MODEL_STYLES)},
                    "question": {"type": "string"},
                    "expected": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["style", "question", "expected"],
            },
        }
    },
    "required": ["questions"],
}

GEN_SYSTEM = """You write TEST QUESTIONS for the internal AI assistant of Turonbank (a bank in Uzbekistan). Bank employees ask it about the bank's products, tariffs and procedures. You receive ONE knowledge-base DOCUMENT. Write exactly one question for each style below, the way a real employee would type it in a chat:

- "formal": a clear, polite question in Uzbek (Latin script) about the main conditions of this product/topic.
- "colloquial": a short, informal Uzbek (Latin) question, the way people type quickly ("avtokredit foizi qancha", "omonatga qancha muddatga qo'ysa bo'ladi"). Do NOT copy the document title word for word — use the words an employee would use.
- "typo": an Uzbek (Latin) question with realistic typos and missing apostrophes ("kredt", "foyz", "olsa boladimi").
- "detail": an Uzbek (Latin) question about ONE specific detail from the document (a number, a required document, an age limit, a fee) — not the main rate.
- "russian": the question in Russian.
- "absent": an Uzbek (Latin) question about this product asking for a detail that is clearly NOT in the document (e.g. a condition or number the document does not mention). The correct answer is that the information was not found.

Rules:
- Every question (except "absent") must be answerable from the DOCUMENT alone.
- Name the product or topic so the question makes sense without the document (an employee does not see it), but do not paste the full title.
- "expected": 1-4 SHORT facts copied from the DOCUMENT that a correct answer MUST contain (numbers with units, e.g. "26,9%", "60 oygacha", "pasport"). For "absent" — an empty list.
Output JSON only."""


def documents_from_points(points: list[dict[str, Any]]) -> dict[str, str]:
    """Qdrant bo'laklari -> {sarlavha: to'liq matn}. Xodimlar ma'lumotnomasi va
    valyuta kursi (kunda o'zgaradi) stendga kirmaydi."""
    chunks: dict[str, list[tuple[int, str]]] = {}
    skip: set[str] = set()
    for p in points:
        title = str(p.get("title") or "").strip()
        if not title:
            continue
        if p.get("doc_type") == "employee" or p.get("rates_json"):
            skip.add(title)
            continue
        chunks.setdefault(title, []).append(
            (int(p.get("chunk_index") or 0), str(p.get("chunk_text") or ""))
        )
    return {
        title: "\n".join(text for _, text in sorted(parts))
        for title, parts in chunks.items()
        if title not in skip
    }


def _lang_of(style: str) -> str:
    if style == "russian":
        return "ru"
    if style == "cyrillic":
        return "uz_cyrl"
    return "uz"


def parse_cases(title: str, data: Any) -> list[EvalCase]:
    """Model javobi -> savollar. Buzuq bandlar tashlanadi; har uslubdan bitta."""
    items = data.get("questions") if isinstance(data, dict) else None
    out: list[EvalCase] = []
    seen: set[str] = set()
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        style = str(item.get("style", "")).strip()
        question = str(item.get("question", "")).strip()
        if style not in _MODEL_STYLES or style in seen or not question:
            continue
        seen.add(style)
        raw = item.get("expected")
        expected = [str(x).strip() for x in raw if str(x).strip()] if isinstance(raw, list) else []
        if style == "absent":
            expected = []
        out.append(EvalCase(title, question, style, _lang_of(style), expected[:4]))
    # Kirill varianti — og'zaki savolning o'zi, kod bilan o'girilgan
    colloquial = next((c for c in out if c.style == "colloquial"), None)
    if colloquial is not None:
        out.append(
            EvalCase(
                title,
                to_cyrillic(colloquial.question),
                "cyrillic",
                "uz_cyrl",
                list(colloquial.expected),
            )
        )
    return out


async def generate_cases(ai_client: BaseAIClient, title: str, text: str) -> list[EvalCase]:
    """Bitta hujjat uchun savollar. Model yiqilsa — bo'sh ro'yxat (stend
    qolgan hujjatlar bilan davom etadi)."""
    prompt = f"DOCUMENT TITLE: {title}\n\nDOCUMENT:\n{text[:GEN_DOC_CHARS]}"
    try:
        result = await ai_client.generate_json(
            prompt,
            schema=GEN_SCHEMA,
            temperature=0.7,
            max_tokens=GEN_MAX_TOKENS,
            system_prompt=GEN_SYSTEM,
            timeout=GEN_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # noqa: BLE001 — bitta hujjat stendni to'xtatmasin
        logger.warning("Stend: savol tuzilmadi %r: %s", title, exc)
        return []
    return parse_cases(title, result.data)
