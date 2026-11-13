"""Javob TEKSHIRUVCHISI — javob foydalanuvchiga chiqishidan OLDIN.

Muammo: botda so'zga qarab ishlaydigan ko'p "qisqa yo'l" bor (turkum ro'yxati,
filiallar, xodimlar, aniqlashtirish). Ular savolni TUSHUNMAYDI — "filial"
so'zi bo'lsa ro'yxat beradi, holbuki savol "filial ochish rejalari" haqida
edi. Har yangi xatoni so'zma-so'z yamash cheksiz yo'l.

Yechim: tayyor javobni o'sha kuchli modelning o'zi baholaydi — "bu javob AYNAN
shu savolga javobmi? kontekstda yo'q raqam/shart to'qilmaganmi?". Mos
bo'lmasa, javob tekshiruvchi ko'rsatgan kamchilik bilan QAYTA yoziladi
(qisqa yo'llarsiz, to'liq qidiruv bilan). Ikkinchisi ham o'tmasa —
noto'g'ri javob o'rniga halol "topilmadi".

Tekshiruvchi YIQILSA (timeout, Ollama xatosi) javob to'xtatilmaydi —
"tekshirilmadi" deb o'tkaziladi: tekshiruv xizmatni to'xtatib qo'ymasligi kerak.
"""

from dataclasses import dataclass
from typing import Any

from loggers import get_logger
from src.core.ai.interfaces import BaseAIClient
from src.knowledge.schemas import ChatTurn

logger = get_logger(__name__)

# Kontekst juda uzun bo'lsa — boshi (eng mos bloklar) qoladi. 65k oynada
# bemalol sig'adi, lekin tekshiruv tez bo'lishi uchun cheklaymiz.
_MAX_CONTEXT_CHARS = 24000
_MAX_ANSWER_CHARS = 8000
# Tekshiruv bitta qisqa JSON — router kabi tez bo'lishi kerak
VERIFY_TIMEOUT_SECONDS = 40.0
VERIFY_MAX_TOKENS = 300

VERIFY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["ok", "wrong"]},
        "problem": {"type": "string"},
        "source": {
            "type": "string",
            "enum": ["knowledge_base", "general_knowledge", "web", "none"],
        },
    },
    "required": ["verdict", "problem", "source"],
}

VERIFY_SYSTEM = """You are a strict quality reviewer for the internal AI assistant of Turonbank (a bank in Uzbekistan). Bank employees ask questions in Uzbek (Latin or Cyrillic) or Russian. You receive the USER QUESTION (with recent conversation), the DRAFT ANSWER, and sometimes the CONTEXT (knowledge-base blocks the answer was supposed to use).

Decide whether the DRAFT ANSWER may be shown to the employee.

Return verdict "wrong" ONLY for a real defect:
1. OFF-TARGET: the answer addresses a different question or topic than the one asked. Examples: the user asks about plans to open new branches, but the answer is just a list of existing branches; the user asks who is responsible for a system, but the answer is a list of unrelated products; the user asks about one product, but the answer describes another product.
1a. WRONG SUBJECT: the question is about another organization or entity (the Central Bank of Uzbekistan / "Markaziy bank" / "ЦБ", another bank, a ministry, a law, a payment system) but the answer talks about Turonbank itself — or the other way round.
1b. WRONG TIME: the question asks for news, latest/recent/current events or today's state ("yangiliklar", "so'nggi", "hozir", "новости"), but the answer gives old historical facts (founding year, past awards) as if they were news.
IMPORTANT: an answer that is fully supported by the CONTEXT is still "wrong" if it is about a different subject, entity or time than the question. The CONTEXT may simply be the wrong document.
2. MISREAD TERM: the answer replaced the user's term with a different, similar-looking word and answered about that instead (e.g. "kontr kafolat" (counter-guarantee) answered as "kontrakt" (contract); "omonat" answered as "kredit").
3. UNSUPPORTED FACT: CONTEXT is given and the answer states a concrete Turonbank fact (interest rate, amount, term, fee, date, phone, address, person, condition) that is NOT in the CONTEXT or contradicts it. General textbook explanations of banking terms are allowed if they are not presented as Turonbank's own conditions.
4. WRONG REFUSAL: the answer says the topic is outside banking/Turonbank, or refuses, although the question is clearly about banking, finance, Turonbank or its employees.
5. WRONG LIST: the answer is a list (products, branches, employees) but the question did not ask for that list, or the list contains items clearly unrelated to the question.
6. SELF-CONTRADICTION or obviously broken text.

Return verdict "ok" when:
- the answer addresses what was asked, even if short or not exhaustive;
- the answer honestly says the information was not found;
- the answer is a relevant clarifying question (e.g. offers options that match the user's words);
- the user's message is a follow-up (a number choosing from a previous list, "yes", "more details") and the answer fits the conversation.
Do NOT nitpick style, length, formatting or language. Do NOT mark "wrong" because you personally do not know a Turonbank fact — judge facts only against the CONTEXT.

"problem": if "wrong" — one short sentence in English naming exactly what is wrong and what the user actually asked for. If "ok" — empty string.
"source": where a correct answer to THIS question should come from:
- "knowledge_base" — Turonbank's own internal data (its products, tariffs, branches, employees, documents, internal procedures);
- "general_knowledge" — general banking/finance knowledge or facts about other well-known institutions (what the Central Bank is and does, what a term means) that a knowledgeable banker can explain without Turonbank documents;
- "web" — fresh or official external facts (news, latest events, today's official rates or decisions, current laws or regulator rules);
- "none" — greetings, follow-ups, or when the answer is ok and no other source is needed.
Output JSON only."""


@dataclass
class Verdict:
    ok: bool
    problem: str
    tokens: int = 0
    # Javob qayerdan olinishi kerak: knowledge_base | general_knowledge | web | none
    source: str = "none"


def _history_tail(history: list[ChatTurn] | None, turns: int = 4) -> str:
    """Oxirgi bir necha almashinuv — "19", "ha" kabi davom savollarni
    tushunish uchun."""
    if not history:
        return ""
    lines = []
    for t in history[-turns:]:
        who = "USER" if t.role == "user" else "ASSISTANT"
        lines.append(f"{who}: {t.content.strip()[:1200]}")
    return "\n".join(lines)


def build_verify_prompt(
    question: str,
    answer: str,
    history: list[ChatTurn] | None = None,
    interpreted: str | None = None,
    context: str | None = None,
) -> str:
    parts: list[str] = []
    tail = _history_tail(history)
    if tail:
        parts.append(f"RECENT CONVERSATION:\n{tail}")
    parts.append(f"USER QUESTION:\n{question.strip()}")
    if interpreted and interpreted.strip() and interpreted.strip() != question.strip():
        parts.append(f"(The system interpreted the question as: {interpreted.strip()})")
    if context:
        parts.append(f"CONTEXT:\n{context[:_MAX_CONTEXT_CHARS]}")
    parts.append(f"DRAFT ANSWER:\n{answer.strip()[:_MAX_ANSWER_CHARS]}")
    return "\n\n".join(parts)


async def verify_answer(
    ai_client: BaseAIClient,
    question: str,
    answer: str,
    history: list[ChatTurn] | None = None,
    interpreted: str | None = None,
    context: str | None = None,
) -> Verdict | None:
    """Javobni baholaydi. None — tekshiruv bajarilmadi (xato/timeout)."""
    prompt = build_verify_prompt(question, answer, history, interpreted, context)
    try:
        result = await ai_client.generate_json(
            prompt,
            schema=VERIFY_SCHEMA,
            temperature=0.0,
            max_tokens=VERIFY_MAX_TOKENS,
            system_prompt=VERIFY_SYSTEM,
            timeout=VERIFY_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # noqa: BLE001 — tekshiruv javobni to'xtatmasin
        logger.warning("Javob tekshiruvi bajarilmadi: %s | %r", exc, question[:200])
        return None
    data = result.data if isinstance(result.data, dict) else {}
    verdict = str(data.get("verdict", "")).strip().lower()
    if verdict not in ("ok", "wrong"):
        logger.warning("Tekshiruvchi noto'g'ri format qaytardi: %r", data)
        return None
    tokens = int((result.usage or {}).get("completion_tokens", 0) or 0)
    problem = str(data.get("problem", "")).strip()[:500]
    source = str(data.get("source", "none")).strip().lower()
    if source not in ("knowledge_base", "general_knowledge", "web", "none"):
        source = "none"
    # Har baho logda — tekshiruvchi qanday ishlayotganini kuzatish uchun
    logger.info(
        "Tekshiruv: %s | manba=%s | %r | %s",
        verdict,
        source,
        question[:120],
        problem or "-",
    )
    return Verdict(ok=verdict == "ok", problem=problem, tokens=tokens, source=source)
