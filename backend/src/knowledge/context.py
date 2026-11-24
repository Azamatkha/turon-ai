"""Topilgan bo'laklarni model uchun KONTEKST matniga aylantirish.

Oddiy RAG javobi (`AnswerQuestionUseCase._assemble`) ham, tool-calling
agentining `search_knowledge` asbobi ham bir xil formatdan foydalanadi —
model hujjat sarlavhasi, manba havolasi, muddati va mijoz turini doim bir
xil ko'rinishda ko'rsin."""

from typing import Any

from src.knowledge.categories import AUDIENCE_PROMPT
from src.knowledge.schemas import SourceRef
from src.knowledge.validity import is_expired


def context_blocks(results: list[tuple[dict[str, Any], float]], budget: int) -> str:
    """Bo'laklar -> "[sarlavha]\nSOURCE_URL: ...\nmatn" bloklari, `budget`
    belgigacha. Byudjet tugasa qolganlari tashlanadi (ular eng kam mos)."""
    # MUHIM: manba havolasi "SOURCE_URL:" yorlig'i bilan beriladi — avval
    # "(Manba: url)" edi va model uni javobga AYNAN ko'chirib, "Batafsil:
    # url(Manba: url)" kabi ikki marta havola chiqarardi (dubl link bug).
    blocks: list[str] = []
    used = 0
    for payload, _ in results:
        title = payload.get("title", "")
        source_url = payload.get("source_url", "")
        header = f"[{title}]\nSOURCE_URL: {source_url}" if source_url else f"[{title}]"
        if is_expired(payload):
            header += (
                f"\nNOTE: this document was valid until {payload.get('valid_until')}; "
                "say in your answer that the information may be outdated and "
                "should be confirmed."
            )
        # Mijoz turi (admin belgilagan) — model mahsulot kimga ekanini
        # bilsin: yuridik shaxs so'raganda jismoniylar mahsulotini taklif
        # qilmasin
        audience = AUDIENCE_PROMPT.get(str(payload.get("audience") or ""))
        if audience:
            header += f"\nFOR CLIENTS: {audience}"
        block = f"{header}\n{payload.get('chunk_text', '')}"
        if blocks and used + len(block) > budget:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n---\n\n".join(blocks)


def source_refs(results: list[tuple[dict[str, Any], float]]) -> list[SourceRef]:
    """Manbalar — sarlavha bo'yicha takrorlanmas."""
    sources: list[SourceRef] = []
    seen: set[str] = set()
    for payload, score in results:
        title = str(payload.get("title", ""))
        if title and title not in seen:
            seen.add(title)
            sources.append(SourceRef(title=title, score=round(score, 3)))
    return sources
