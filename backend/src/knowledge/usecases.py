from typing import Any

from src.core.ai.embeddings import OllamaEmbedder
from src.core.ai.interfaces import BaseAIClient
from src.core.errors.exceptions import (
    InstanceNotFoundException,
    InstanceProcessingException,
)
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge.chunking import chunk_text
from src.knowledge.prompts import RAG_SYSTEM
from src.knowledge.scraper import extract_content, fetch_html
from src.knowledge.schemas import (
    AnswerResult,
    ChatTurn,
    KnowledgeChunk,
    KnowledgeDetail,
    KnowledgeItem,
    SourceRef,
    UploadResult,
)


class UploadKnowledgeUseCase:
    def __init__(self, embedder: OllamaEmbedder, store: QdrantStore) -> None:
        self.embedder = embedder
        self.store = store

    async def execute(
        self, title: str, text: str, source_url: str = ""
    ) -> UploadResult:
        chunks = chunk_text(text)
        if not chunks:
            raise InstanceProcessingException("Matn bo'sh — yozadigan narsa yo'q")

        vectors: list[list[float]] = []
        payloads: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks):
            # Sarlavhani har bo'lakka qo'shib embed qilamiz — kontekst kuchayadi
            vector = await self.embedder.embed(f"{title}\n\n{chunk}")
            vectors.append(vector)
            payloads.append(
                {
                    "title": title,
                    "chunk_text": chunk,
                    "chunk_index": index,
                    "lang": "uz",
                    "source_url": source_url,  # manba havolasi (parsing uchun)
                }
            )

        dim = len(vectors[0])
        await self.store.ensure_collection(dim)
        await self.store.upsert(vectors, payloads)
        total = await self.store.count()
        return UploadResult(chunks=len(chunks), vector_dim=dim, total_points=total)


class ScrapeUrlUseCase:
    """Bitta URL'ni ochib, toza matnini ajratib, bazaga yozadi (parsing)."""

    def __init__(self, embedder: OllamaEmbedder, store: QdrantStore) -> None:
        self.embedder = embedder
        self.store = store

    async def execute(self, url: str) -> UploadResult:
        html = await fetch_html(url)
        title, text = extract_content(html, url)
        if not text:
            raise InstanceProcessingException(
                "Sahifadan matn ajratib bo'lmadi (bo'sh yoki nomatn sahifa)"
            )
        return await UploadKnowledgeUseCase(
            embedder=self.embedder, store=self.store
        ).execute(title=title, text=text, source_url=url)


class ListKnowledgeUseCase:
    def __init__(self, store: QdrantStore) -> None:
        self.store = store

    async def execute(self) -> list[KnowledgeItem]:
        # Kolleksiya hali yaratilmagan bo'lsa — bo'sh ro'yxat
        if not await self.store.exists():
            return []

        payloads = await self.store.scroll_all()

        # Sarlavha bo'yicha guruhlaymiz: har sarlavha ostida nechta bo'lak bor
        grouped: dict[str, dict[str, Any]] = {}
        for payload in payloads:
            title = str(payload.get("title", ""))
            group = grouped.setdefault(
                title,
                {"chunks": 0, "lang": str(payload.get("lang", "")), "preview": ""},
            )
            group["chunks"] += 1
            # Birinchi bo'lak (chunk_index == 0) matnidan qisqa ko'rinish olamiz
            if payload.get("chunk_index") == 0:
                group["preview"] = str(payload.get("chunk_text", ""))[:160]

        return [
            KnowledgeItem(
                title=title,
                chunks=data["chunks"],
                lang=data["lang"],
                preview=data["preview"],
            )
            for title, data in grouped.items()
        ]


class GetKnowledgeDetailUseCase:
    def __init__(self, store: QdrantStore) -> None:
        self.store = store

    async def execute(self, title: str) -> KnowledgeDetail:
        if not await self.store.exists():
            raise InstanceNotFoundException("Ma'lumot topilmadi")

        payloads = await self.store.scroll_all()
        matching = [p for p in payloads if str(p.get("title", "")) == title]
        if not matching:
            raise InstanceNotFoundException("Ma'lumot topilmadi")

        matching.sort(key=lambda p: int(p.get("chunk_index", 0)))
        chunks = [
            KnowledgeChunk(
                chunk_index=int(payload.get("chunk_index", 0)),
                text=str(payload.get("chunk_text", "")),
            )
            for payload in matching
        ]
        lang = str(matching[0].get("lang", ""))
        return KnowledgeDetail(title=title, lang=lang, chunks=chunks)


class DeleteKnowledgeUseCase:
    def __init__(self, store: QdrantStore) -> None:
        self.store = store

    async def execute(self, title: str) -> None:
        await self.store.delete_by_title(title)


class UpdateKnowledgeUseCase:
    """Tahrirlash = eski sarlavha bo'laklarini o'chirib, yangi matnni qayta yozish."""

    def __init__(self, embedder: OllamaEmbedder, store: QdrantStore) -> None:
        self.embedder = embedder
        self.store = store

    async def execute(
        self, old_title: str, title: str, text: str
    ) -> UploadResult:
        await self.store.delete_by_title(old_title)
        return await UploadKnowledgeUseCase(
            embedder=self.embedder, store=self.store
        ).execute(title=title, text=text)


class AnswerQuestionUseCase:
    """RAG: savolni embed qiladi, Qdrant'dan eng yaqin bo'laklarni topadi va
    ularni kontekst sifatida Qwen'ga berib javob oldiradi."""

    TOP_K = 4
    TEMPERATURE = 0.2
    MAX_TOKENS = 2048  # qwen "o'ylash" + javob sig'ishi uchun yetarli
    HISTORY_LIMIT = 10  # oxirgi shuncha xabar (mavzu davomiyligi uchun)

    def __init__(
        self,
        embedder: OllamaEmbedder,
        store: QdrantStore,
        ai_client: BaseAIClient,
    ) -> None:
        self.embedder = embedder
        self.store = store
        self.ai_client = ai_client

    async def execute(
        self, question: str, history: list[ChatTurn] | None = None
    ) -> AnswerResult:
        query_vector = await self.embedder.embed(question)
        results = await self.store.search(query_vector, top_k=self.TOP_K)

        # HOZIRCHA: kontekst topilsa — undan foydalanamiz; topilmasa — umumiy javob.
        if results:
            context = "\n\n---\n\n".join(
                f"[{payload.get('title', '')}]\n{payload.get('chunk_text', '')}"
                for payload, _ in results
            )
            base = f"MA'LUMOT (kontekst):\n{context}\n\nSAVOL: {question}"
        else:
            base = f"SAVOL: {question}"

        # Oldingi suhbatni (oxirgi HISTORY_LIMIT ta) promptga qo'shamiz
        if history:
            recent = history[-self.HISTORY_LIMIT :]
            convo = "\n".join(
                f"{'Foydalanuvchi' if t.role == 'user' else 'Yordamchi'}: {t.content}"
                for t in recent
            )
            prompt = f"Oldingi suhbat:\n{convo}\n\n{base}"
        else:
            prompt = base

        answer = await self.ai_client.generate_text(
            prompt,
            system_prompt=RAG_SYSTEM,
            temperature=self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS,
        )

        # Manbalarni sarlavha bo'yicha takrorlanmas qilib yig'amiz
        sources: list[SourceRef] = []
        seen: set[str] = set()
        for payload, score in results:
            title = str(payload.get("title", ""))
            if title and title not in seen:
                seen.add(title)
                sources.append(SourceRef(title=title, score=round(score, 3)))

        return AnswerResult(answer=answer.strip(), sources=sources)
