"""
Savol-javob oqimini boshqaradi (RAG yadrosi):

    savol -> retriever (Qdrant) -> kontekst -> LLM -> javob + manbalar

LLM uchun template'dagi mavjud AI mijoz (src.core.ai) qayta ishlatiladi.
"""
import asyncio

from src.core.ai.interfaces import BaseAIClient
from src.core.errors.exceptions import InstanceNotFoundException
from src.main.config import config

SYSTEM_PROMPT = (
    "Siz Turon Bank xodimlari uchun ichki AI yordamchisiz. "
    "Faqat berilgan KONTEKST asosida javob bering. "
    "Agar javob kontekstda bo'lmasa, buni ochiq ayting va o'ylab topmang. "
    "Savol qaysi tilda bo'lsa (o'zbek yoki rus), o'sha tilda javob bering."
)


class AskService:
    def __init__(self, ai_client: BaseAIClient) -> None:
        self._ai = ai_client

    async def savol_ber(self, savol: str, top_k: int | None = None) -> dict:
        # RAG'ni shu yerda import qilamiz (og'ir kutubxonalarni ilova startida tortmaslik uchun)
        from src.rag.retriever import qidir

        # qidir() sinxron (embeddings + qdrant) — event loop'ni bloklamaslik uchun thread'da
        boluklar = await asyncio.to_thread(qidir, savol, top_k)
        if not boluklar:
            raise InstanceNotFoundException("Savolga mos hujjat topilmadi")

        javob = await self._ai.generate_text(
            prompt=f"KONTEKST:\n{self._kontekst(boluklar)}\n\nSAVOL: {savol}",
            system_prompt=SYSTEM_PROMPT,
            temperature=config.ai.DEFAULT_TEMPERATURE,
            max_tokens=config.ai.DEFAULT_MAX_TOKENS,
        )
        return {"javob": javob, "manbalar": self._manbalar(boluklar)}

    @staticmethod
    def _kontekst(boluklar: list) -> str:
        return "\n\n".join(
            f"[{i}] Manba: {b.manba} | Mavzu: {b.sarlavha}\n{b.matn}"
            for i, b in enumerate(boluklar, start=1)
        )

    @staticmethod
    def _manbalar(boluklar: list) -> list[dict]:
        korilgan: set[str] = set()
        natija: list[dict] = []
        for b in boluklar:
            if b.manba in korilgan:
                continue
            korilgan.add(b.manba)
            natija.append(
                {"manba": b.manba, "sarlavha": b.sarlavha, "ishonch": round(b.score, 3)}
            )
        return natija
