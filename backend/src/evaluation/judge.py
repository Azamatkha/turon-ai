"""Hakam: botning javobini ASL HUJJAT bilan solishtiradi.

Botning ichki tekshiruvchisidan (knowledge/verifier.py) farqi: u faqat qidiruv
topgan bo'laklarni ko'radi, shuning uchun qidiruv noto'g'ri hujjatni olib
kelsa yoki umuman topmasa, buni bilolmaydi. Hakam esa to'g'ri hujjatni va
majburiy faktlarni biladi — "qidiruv topmadi" va "to'qib yubordi" ni ajrata oladi.
"""

from dataclasses import dataclass
from typing import Any

from loggers import get_logger
from src.core.ai.interfaces import BaseAIClient
from src.core.utils.uzbek_script import is_cyrillic_text
from src.evaluation.schemas import FAILURES, EvalCase
from src.knowledge.lang import is_russian_text

logger = get_logger(__name__)

JUDGE_DOC_CHARS = 12000
JUDGE_ANSWER_CHARS = 6000
JUDGE_TIMEOUT_SECONDS = 60.0
JUDGE_MAX_TOKENS = 400
# Tilni tekshirish uchun javobda kamida shuncha harf bo'lsin ("OK", raqamlar
# ro'yxati kabi qisqa javobda alifbo hech narsa aytmaydi)
_LANG_MIN_LETTERS = 40

# Hakam tanlaydigan turlar. "retrieval_miss" va "wrong_language" — kod
# aniqlaydi (manbalar va alifbo bo'yicha), hakam emas.
_JUDGE_FAILURES = ("misunderstood", "not_found", "hallucination", "incomplete", "refused")

JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "passed": {"type": "boolean"},
        "failure": {"type": "string", "enum": ["none", *_JUDGE_FAILURES]},
        "note": {"type": "string"},
    },
    "required": ["passed", "failure", "note"],
}

JUDGE_SYSTEM = """You grade answers of the internal AI assistant of Turonbank (a bank in Uzbekistan). You receive a TEST QUESTION, the REFERENCE DOCUMENT that contains the true answer, the EXPECTED FACTS a correct answer must contain, and the ASSISTANT ANSWER.

The REFERENCE DOCUMENT is the ground truth. Grade only the content, not style, length or formatting. Numbers may be formatted differently ("26,9%" = "26.9 %", "60 oy" = "5 yil") — that is fine.

If the question style is "absent", the document does NOT contain the requested detail: the answer PASSES if it says the detail was not found / is not specified (it may add correct facts from the document); it FAILS as "hallucination" if it states a concrete value for that detail.

Otherwise the answer PASSES when it answers the question and contains the EXPECTED FACTS (or equivalent values) and states nothing that contradicts the document. Otherwise choose the failure:
- "misunderstood": the answer is about a different product/topic or a different question.
- "not_found": the answer says the information was not found or not available, although the document has it.
- "hallucination": the answer states a concrete fact (rate, amount, term, fee, condition) that is not in the document or contradicts it.
- "incomplete": on topic and nothing false, but one or more EXPECTED FACTS are missing.
- "refused": the answer refuses or says the topic is out of scope.

"note": IN UZBEK (Latin script), one or two short sentences for the bank's admin: what is wrong (or "To'g'ri" if passed).
Output JSON only."""


@dataclass
class Grade:
    passed: bool
    failure: str
    note: str


def language_ok(answer: str, lang: str) -> bool:
    """Javob savol tilidami — alifbo bo'yicha, model chaqirilmaydi."""
    if sum(1 for c in answer if c.isalpha()) < _LANG_MIN_LETTERS:
        return True
    if lang == "ru":
        return is_russian_text(answer)
    if lang == "uz_cyrl":
        return is_cyrillic_text(answer) and not is_russian_text(answer)
    return not is_cyrillic_text(answer)


def build_judge_prompt(case: EvalCase, answer: str, document: str) -> str:
    expected = "\n".join(f"- {f}" for f in case.expected) or "(none)"
    return (
        f"QUESTION STYLE: {case.style}\n\n"
        f"TEST QUESTION:\n{case.question}\n\n"
        f"REFERENCE DOCUMENT ({case.doc_title}):\n{document[:JUDGE_DOC_CHARS]}\n\n"
        f"EXPECTED FACTS:\n{expected}\n\n"
        f"ASSISTANT ANSWER:\n{answer.strip()[:JUDGE_ANSWER_CHARS]}"
    )


async def judge_answer(
    ai_client: BaseAIClient, case: EvalCase, answer: str, document: str
) -> Grade:
    """Baho. Hakam yiqilsa — "error" (o'tmadi deb hisoblanmaydi, hisobotda
    alohida ko'rinadi)."""
    if not answer.strip():
        return Grade(False, "not_found", "Javob bo'sh.")
    try:
        result = await ai_client.generate_json(
            build_judge_prompt(case, answer, document),
            schema=JUDGE_SCHEMA,
            temperature=0.0,
            max_tokens=JUDGE_MAX_TOKENS,
            system_prompt=JUDGE_SYSTEM,
            timeout=JUDGE_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Stend hakami yiqildi: %r: %s", case.question[:120], exc)
        return Grade(False, "error", "Hakam baholay olmadi.")
    data = result.data if isinstance(result.data, dict) else {}
    passed = bool(data.get("passed"))
    failure = str(data.get("failure", "")).strip()
    note = str(data.get("note", "")).strip()[:600]
    if passed:
        return Grade(True, "", note)
    if failure not in FAILURES:
        failure = "incomplete"
    return Grade(False, failure, note)
