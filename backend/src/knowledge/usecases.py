import re
from collections.abc import AsyncIterator
from typing import Any

from src.core.ai.embeddings import OllamaEmbedder
from src.core.ai.interfaces import BaseAIClient
from src.core.errors.exceptions import (
    InfrastructureException,
    InstanceNotFoundException,
    InstanceProcessingException,
)
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge.chunking import chunk_text
from src.knowledge.employee_parser import parse_employees
from src.knowledge.prompts import (
    EMPLOYEE_ASK_REPLY,
    EMPLOYEE_SYSTEM,
    NO_INFO_REPLY,
    STRICT_RAG_SYSTEM,
)
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


# ------- Xodim (telefon/IP ma'lumotnoma) qidiruv yordamchilari ------- #
# Xodimlar ma'lumoti STRUKTURAVIY — IP/telefon/ism bo'yicha ANIQ moslash embedding
# semantik qidiruvidan ishonchliroq (raqamlar semantik qidiruvda yomon topiladi).

_NAME_STOP = {"ogli", "ugli", "qizi", "kizi"}
_DEPT_STOP = {
    "departamenti", "departament", "departmenti", "dep", "bolim", "bolimi",
    "boshqarish", "boshqarmasi", "xodimlar", "xodimlarni", "xodim", "va", "ip",
    "raqam", "raqami", "raqamlari", "telefon", "markazi", "xizmatlari", "xizmat",
    "nazorat", "hisobini", "yuritish", "bosh", "menejer", "direktori",
}


def _words(s: str) -> list[str]:
    return re.findall(r"[0-9a-zа-яёўқғҳ]+", s.lower())


def _match_employees(
    emps: list[dict[str, Any]], q_lower: str
) -> list[dict[str, Any]]:
    """Savolga mos xodimlarni ANIQ moslash bilan topadi: IP raqami, telefon,
    bo'lim nomi yoki F.I.SH bo'yicha. Topilmasa bo'sh ro'yxat."""
    qwords = set(_words(q_lower))
    nums = re.findall(r"\d{3,}", q_lower)

    # 1) IP (qisqa raqam) — aniq tenglik
    ip_targets = {n for n in nums if len(n) <= 5}
    if ip_targets:
        hit = [e for e in emps if str(e.get("ip", "")).strip() in ip_targets]
        if hit:
            return hit

    # 2) Telefon (uzun raqam) — raqamlarini solishtirib qism moslash
    phone_targets = [re.sub(r"\D", "", n) for n in nums if len(n) >= 7]
    if phone_targets:
        hit = [
            e
            for e in emps
            if any(
                pt and pt in re.sub(r"\D", "", str(e.get("phone", "")))
                for pt in phone_targets
            )
        ]
        if hit:
            return hit

    # 3) Bo'lim nomi — turkumning o'ziga xos so'zi savolda bo'lsa, o'sha bo'lim hammasi.
    # Qo'shimchalarni (masalan "riskdan") ushlash uchun uzunroq so'zlarda substring.
    for dept in {str(e.get("department", "")) for e in emps}:
        distinctive = [
            t for t in _words(dept) if len(t) >= 2 and t not in _DEPT_STOP
        ]
        if distinctive and any(
            t in qwords or (len(t) >= 4 and t in q_lower) for t in distinctive
        ):
            return [e for e in emps if str(e.get("department", "")) == dept]

    # 4) F.I.SH — ismning muhim so'zlari (deyarli hammasi) savolda bo'lsa.
    # substring: o'zbekcha qo'shimcha (-ning, -ga ...) ismga yopishsa ham topsin.
    named: list[dict[str, Any]] = []
    for e in emps:
        toks = [
            t
            for t in _words(str(e.get("fish", "")))
            if len(t) >= 3 and t not in _NAME_STOP
        ]
        if len(toks) < 2:
            continue
        present = sum(1 for t in toks if t in q_lower)
        if present >= 2 and present >= len(toks) - 1:
            named.append(e)
    return named


def _is_generic_employee_request(q_lower: str) -> bool:
    """"Xodimlar raqamlari" kabi umumiy (aniq xodim/bo'limsiz) so'rovmi —
    aniqlashtirishni so'rash uchun."""
    has_emp = "xodim" in q_lower or "ходим" in q_lower
    has_num = any(
        w in q_lower for w in ("raqam", "ip", "telefon", "рақам", "телефон")
    )
    return has_emp and has_num and len(_words(q_lower)) <= 5


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
        try:
            for index, chunk in enumerate(chunks):
                # Sarlavhani har bo'lakka qo'shib embed qilamiz — kontekst kuchayadi
                # Sarlavhani nafaqat embedding uchun, balki saqlanadigan matnning
                # o'ziga ham yozamiz — shunda bo'lak yolg'iz o'qilganda ham
                # (masalan boshqa kartalarnikiga aralashib qolmasdan) qaysi
                # mahsulotga tegishli ekani aniq bo'ladi.
                chunk_with_title = f"{title}\n\n{chunk}"
                vector = await self.embedder.embed(chunk_with_title)
                vectors.append(vector)
                payloads.append(
                    {
                        "title": title,
                        "chunk_text": chunk_with_title,
                        "chunk_index": index,
                        "lang": "uz",
                        "source_url": source_url,  # manba havolasi (parsing uchun)
                    }
                )
        except Exception as exc:
            raise InfrastructureException(
                f"Embedding xizmati bilan bog'lanib bo'lmadi: {type(exc).__name__}: {exc!r}"
            ) from exc

        try:
            dim = len(vectors[0])
            await self.store.ensure_collection(dim)
            await self.store.upsert(vectors, payloads)
            total = await self.store.count()
        except Exception as exc:
            raise InfrastructureException(
                f"Vektor bazasi (Qdrant) bilan bog'lanib bo'lmadi: {type(exc).__name__}: {exc!r}"
            ) from exc
        return UploadResult(chunks=len(chunks), vector_dim=dim, total_points=total)


class UploadEmployeesUseCase:
    """Excel (.xlsx) xodimlar ma'lumotnomasini o'qib, har xodimni alohida nuqta
    sifatida Qdrant'ga yozadi (doc_type=employee, strukturaviy payload bilan).
    Har yuklashda avvalgi xodim nuqtalari tozalanib, fayldagi to'liq ro'yxat
    qayta yoziladi (fayl — yagona haqiqat manbai)."""

    def __init__(self, embedder: OllamaEmbedder, store: QdrantStore) -> None:
        self.embedder = embedder
        self.store = store

    @staticmethod
    def _format(r: dict[str, str]) -> str:
        parts = [f"Bo'lim: {r['department']}"]
        if r["division"]:
            parts.append(f"Bo'linma: {r['division']}")
        if r["position"]:
            parts.append(f"Lavozim: {r['position']}")
        parts.append(f"F.I.SH: {r['fish']}")
        if r["ip"]:
            parts.append(f"Ichki raqam (IP): {r['ip']}")
        if r["phone"]:
            parts.append(f"Telefon: {r['phone']}")
        return ". ".join(parts) + "."

    async def execute(self, file_bytes: bytes) -> UploadResult:
        """Excel (.xlsx) baytlaridan o'qib yozadi."""
        records = parse_employees(file_bytes)
        if not records:
            raise InstanceProcessingException(
                "Excel'dan xodim topilmadi — sarlavha va ustunlarni tekshiring."
            )
        return await self._ingest(records)

    async def execute_records(
        self, records: list[dict[str, str]]
    ) -> UploadResult:
        """Tayyor JSON ro'yxatidan yozadi (Excel'siz — openpyxl kerak emas)."""
        def g(r: dict[str, str], k: str) -> str:
            return str(r.get(k) or "").strip()

        clean = [
            {
                "department": g(r, "department"),
                "division": g(r, "division"),
                "position": g(r, "position"),
                "fish": g(r, "fish"),
                "ip": g(r, "ip"),
                "phone": g(r, "phone"),
            }
            for r in records
            if g(r, "fish") or g(r, "ip") or g(r, "phone")
        ]
        if not clean:
            raise InstanceProcessingException(
                "Ro'yxat bo'sh yoki majburiy maydonlar (fish/ip/phone) topilmadi."
            )
        return await self._ingest(clean)

    async def _ingest(self, records: list[dict[str, str]]) -> UploadResult:
        vectors: list[list[float]] = []
        payloads: list[dict[str, Any]] = []
        try:
            for index, r in enumerate(records):
                text = self._format(r)
                vector = await self.embedder.embed(text)
                vectors.append(vector)
                payloads.append(
                    {
                        "title": r["department"],
                        "chunk_text": text,
                        "chunk_index": index,
                        "lang": "uz",
                        "source_url": "",
                        "doc_type": "employee",
                        "department": r["department"],
                        "division": r["division"],
                        "position": r["position"],
                        "fish": r["fish"],
                        "ip": r["ip"],
                        "phone": r["phone"],
                    }
                )
        except Exception as exc:
            raise InfrastructureException(
                f"Embedding xizmati bilan bog'lanib bo'lmadi: {type(exc).__name__}: {exc!r}"
            ) from exc

        try:
            dim = len(vectors[0])
            await self.store.ensure_collection(dim)
            # FAQAT shu fayldagi bo'limlar xodimlarini almashtiramiz — boshqa
            # bo'limlar saqlanadi (ko'p faylni ketma-ket yuklash mumkin), va
            # o'sha bo'limni qayta yuklaganda dublikat qolmaydi.
            new_depts = {r["department"] for r in records}
            existing = await self.store.scroll_all_records(limit=10000)
            stale = [
                pid
                for pid, p in existing
                if p.get("doc_type") == "employee"
                and p.get("department") in new_depts
            ]
            await self.store.delete_ids(stale)
            await self.store.upsert(vectors, payloads)
            total = await self.store.count()
        except Exception as exc:
            raise InfrastructureException(
                f"Vektor bazasi (Qdrant) bilan bog'lanib bo'lmadi: {type(exc).__name__}: {exc!r}"
            ) from exc
        return UploadResult(chunks=len(records), vector_dim=dim, total_points=total)


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
        title = await self._unique_title(title, url)
        # Qayta scrape qilinganda avvalgi bo'laklarni o'chiramiz — deterministic ID
        # bir xil chunk_index'larni ustiga yozadi, lekin chunk soni kamaysa
        # ortiqcha eski bo'laklar qolib ketmasligi uchun avval tozalaymiz.
        await self.store.delete_by_title(title)
        return await UploadKnowledgeUseCase(
            embedder=self.embedder, store=self.store
        ).execute(title=title, text=text, source_url=url)

    async def _unique_title(self, title: str, url: str) -> str:
        """Boshqa (turli source_url'ga tegishli) yozuv bilan sarlavha
        to'qnashsa — ustidan bosib o'chirib yubormaslik uchun sarlavhani
        havola oxiridan ajratma qo'shib farqlaymiz."""
        if not await self.store.exists():
            return title
        payloads = await self.store.scroll_all()
        collides = any(
            p.get("title") == title
            and p.get("source_url")
            and p.get("source_url") != url
            for p in payloads
        )
        if not collides:
            return title
        slug = url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").strip()
        return f"{title} ({slug})" if slug else title


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

    TOP_K = 6
    TEMPERATURE = 0.2
    # Javob yozish vaqti taxminan token soniga proporsional — sekin hardware'da
    # cheklovni pasaytirsak eng yomon holatdagi kutish qisqaradi. Javoblar odatda
    # 500 tokendan qisqa, shuning uchun 1024 yetarli.
    MAX_TOKENS = 2048
    HISTORY_LIMIT = 6  # oxirgi shuncha xabar (promptni yengil tutish uchun)
    # Eng yaqin bo'lakning cosine o'xshashligi shundan past bo'lsa — savol bazaga
    # aloqasiz (bema'ni yoki mavzudan tashqari) deb hisoblaymiz va LLM'ni umuman
    # chaqirmasdan tayyor "ma'lumotim yo'q" javobini qaytaramiz (tez javob uchun).
    MIN_SCORE = 0.35

    def __init__(
        self,
        embedder: OllamaEmbedder,
        store: QdrantStore,
        ai_client: BaseAIClient,
    ) -> None:
        self.embedder = embedder
        self.store = store
        self.ai_client = ai_client

    @staticmethod
    def _category_label(source_url: str) -> str:
        """source_url yo'lidan mahsulot turkumini aniqlaydi — katalogni
        guruhlash uchun (kartalar / kreditlar / omonatlar ...)."""
        url = source_url.lower()
        if "plastic-card" in url or "/cards" in url or "karta" in url:
            return "Bank kartalari"
        if "credit" in url or "loan" in url or "kredit" in url:
            return "Kreditlar"
        if "deposit" in url or "omonat" in url:
            return "Omonatlar"
        if "transfer" in url or "otkazma" in url or "o-tkazma" in url:
            return "Pul o'tkazmalari"
        return "Boshqa xizmatlar"

    async def _build_catalog(self) -> str:
        """Bazadagi BARCHA mahsulotlarning to'liq ro'yxati (title bo'yicha noyob),
        turkumlarga ajratilgan. Semantik qidiruv faqat eng yaqin bir nechtasini
        topadi — bu esa keng savolga ("barcha kredit turlari") TO'LIQ javob berish
        uchun butun katalogni beradi."""
        payloads = await self.store.scroll_all(limit=2000)
        # title bo'yicha noyob mahsulotlar (birinchi uchragan source_url bilan).
        # Xodimlar (doc_type=employee) mahsulot katalogiga kirmaydi.
        seen: dict[str, str] = {}
        for p in payloads:
            if p.get("doc_type") == "employee":
                continue
            title = str(p.get("title", "")).strip()
            if title and title not in seen:
                seen[title] = str(p.get("source_url", ""))
        if not seen:
            return ""
        # turkumlarga ajratamiz — katalogda faqat NOMLAR (URL kerak emas, chunki
        # ro'yxatda havola qo'yilmaydi; havola aniq mahsulot javobida kontekstdan
        # olinadi). URL'larni tushirish promptni ancha yengillashtiradi.
        groups: dict[str, list[str]] = {}
        for title, url in seen.items():
            label = self._category_label(url)
            groups.setdefault(label, []).append(f"- {title}")
        blocks = [f"### {cat}\n" + "\n".join(items) for cat, items in groups.items()]
        return "\n\n".join(blocks)

    async def _employee_route(
        self, question: str
    ) -> tuple[str, list[dict[str, Any]]] | None:
        """Savol xodim (telefon/IP) haqida bo'lsa yo'naltiradi:
        ("answer", [xodimlar]) — mos xodim(lar) topildi;
        ("ask", []) — umumiy so'rov, aniqlashtirish kerak;
        None — bu xodim savoli emas (mahsulot RAG'ga o'tadi)."""
        # scroll_all + Python filtr — Qdrant'ning payload-filtr indeksi (doc_type)
        # sozlanmagan bo'lsa ham ishonchli ishlaydi (katalog ham shu yo'l bilan).
        all_payloads = await self.store.scroll_all(limit=5000)
        emps = [p for p in all_payloads if p.get("doc_type") == "employee"]
        if not emps:
            return None
        matched = _match_employees(emps, question.lower())
        if matched:
            return "answer", matched[:60]
        if _is_generic_employee_request(question.lower()):
            return "ask", []
        return None

    def _employee_prompt(
        self,
        question: str,
        history: list[ChatTurn] | None,
        emps: list[dict[str, Any]],
    ) -> str:
        context = "\n\n".join(str(e.get("chunk_text", "")) for e in emps)
        base = f"XODIMLAR MA'LUMOTI:\n{context}\n\nSAVOL: {question}"
        if history:
            recent = history[-self.HISTORY_LIMIT :]
            convo = "\n".join(
                f"{'Foydalanuvchi' if t.role == 'user' else 'Yordamchi'}: {t.content}"
                for t in recent
            )
            return f"Oldingi suhbat:\n{convo}\n\n{base}"
        return base

    async def _assemble(
        self,
        question: str,
        history: list[ChatTurn] | None,
        results: list[tuple[dict[str, Any], float]],
    ) -> tuple[str, list[SourceRef]]:
        """Topilgan bo'laklar + to'liq katalog + suhbat tarixidan yakuniy promptni
        va manbalar ro'yxatini quradi (execute/execute_stream uchun umumiy). Katalog
        HAR DOIM qo'shiladi — keng savolda (masalan "Bank kartalari") modelning
        faqat bitta mahsulotni qaytarib qo'yishini oldini oladi; aniq mahsulot
        savolida esa system prompt baribir bitta mahsulot bo'yicha javob berdiradi."""
        # Batafsil kontekst (tanlangan mavzuga oid eng yaqin bo'laklar) —
        # aniq mahsulot bo'yicha to'liq (raqam/shart) javob berish uchun.
        blocks = []
        for payload, _ in results:
            title = payload.get("title", "")
            source_url = payload.get("source_url", "")
            header = f"[{title}] (Manba: {source_url})" if source_url else f"[{title}]"
            blocks.append(f"{header}\n{payload.get('chunk_text', '')}")
        context = "\n\n---\n\n".join(blocks)

        # To'liq katalog — turkumdagi HAMMA mahsulotni sanash uchun (keng savol).
        catalog = await self._build_catalog()
        catalog_block = (
            f"MAHSULOTLAR TO'LIQ KATALOGI (bazadagi barcha mavjud mahsulotlar, "
            f"turkumlar bo'yicha — keng/umumiy savolga shu ro'yxatdan foydalan):\n"
            f"{catalog}\n\n"
            if catalog
            else ""
        )
        base = (
            f"{catalog_block}"
            f"BATAFSIL MA'LUMOT (tanlangan mavzuga oid kontekst):\n{context}\n\n"
            f"SAVOL: {question}"
        )

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

        # Manbalarni sarlavha bo'yicha takrorlanmas qilib yig'amiz
        sources: list[SourceRef] = []
        seen: set[str] = set()
        for payload, score in results:
            title = str(payload.get("title", ""))
            if title and title not in seen:
                seen.add(title)
                sources.append(SourceRef(title=title, score=round(score, 3)))

        return prompt, sources

    async def execute_stream(
        self, question: str, history: list[ChatTurn] | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """execute bilan bir xil RAG mantiqi, lekin javobni token-token (oqim)
        qaytaradi — foydalanuvchi real vaqtda ko'rishi uchun. Har bir bo'lak:
        {"type":"delta","text":...}; oxirida token statistikasi bilan
        {"type":"done", ...}."""
        # Xodim (telefon/IP) savoli — alohida yo'l (mahsulot RAG'siz)
        route = await self._employee_route(question)
        if route is not None:
            kind, emps = route
            if kind == "ask":
                yield {"type": "delta", "text": EMPLOYEE_ASK_REPLY}
                yield {
                    "type": "done",
                    "completion_tokens": 0,
                    "finish_reason": "stop",
                    "max_tokens": self.MAX_TOKENS,
                    "sources": [],
                }
                return
            emp_prompt = self._employee_prompt(question, history, emps)
            async for ev in self.ai_client.stream_generate(
                emp_prompt,
                system_prompt=EMPLOYEE_SYSTEM,
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS,
            ):
                if ev.get("type") == "done":
                    ev["max_tokens"] = self.MAX_TOKENS
                    ev["sources"] = []
                yield ev
            return

        query_vector = await self.embedder.embed(question)
        results = await self.store.search(query_vector, top_k=self.TOP_K)

        top_score = results[0][1] if results else 0.0
        if not results or top_score < self.MIN_SCORE:
            yield {"type": "delta", "text": NO_INFO_REPLY}
            yield {
                "type": "done",
                "completion_tokens": 0,
                "finish_reason": "stop",
                "max_tokens": self.MAX_TOKENS,
                "sources": [],
            }
            return

        prompt, sources = await self._assemble(question, history, results)
        src_dump = [{"title": s.title, "score": s.score} for s in sources]
        async for ev in self.ai_client.stream_generate(
            prompt,
            system_prompt=STRICT_RAG_SYSTEM,
            temperature=self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS,
        ):
            if ev.get("type") == "done":
                ev["max_tokens"] = self.MAX_TOKENS
                ev["sources"] = src_dump
            yield ev

    async def execute(
        self, question: str, history: list[ChatTurn] | None = None
    ) -> AnswerResult:
        # Xodim (telefon/IP) savoli — alohida yo'l (mahsulot RAG'siz)
        route = await self._employee_route(question)
        if route is not None:
            kind, emps = route
            if kind == "ask":
                return AnswerResult(
                    answer=EMPLOYEE_ASK_REPLY,
                    sources=[],
                    finish_reason="stop",
                    completion_tokens=0,
                    max_tokens=self.MAX_TOKENS,
                )
            emp_prompt = self._employee_prompt(question, history, emps)
            gen = await self.ai_client.generate_text_with_usage(
                emp_prompt,
                system_prompt=EMPLOYEE_SYSTEM,
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS,
            )
            return AnswerResult(
                answer=gen.text.strip(),
                sources=[],
                finish_reason=gen.finish_reason,
                completion_tokens=gen.completion_tokens,
                max_tokens=gen.max_tokens,
            )

        query_vector = await self.embedder.embed(question)
        results = await self.store.search(query_vector, top_k=self.TOP_K)

        # Mos kontekst yo'q (yoki eng yaqini ham juda uzoq) — LLM'ni chaqirmasdan
        # darrov "ma'lumotim yo'q" deb qaytaramiz. Bu bema'ni/aloqasiz savolga
        # modelning uzoq (bir necha daqiqa) "o'ylab" javob berishini oldini oladi.
        top_score = results[0][1] if results else 0.0
        if not results or top_score < self.MIN_SCORE:
            return AnswerResult(
                answer=NO_INFO_REPLY,
                sources=[],
                finish_reason="stop",
                completion_tokens=0,
                max_tokens=self.MAX_TOKENS,
            )

        prompt, sources = await self._assemble(question, history, results)

        gen = await self.ai_client.generate_text_with_usage(
            prompt,
            system_prompt=STRICT_RAG_SYSTEM,
            temperature=self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS,
        )

        return AnswerResult(
            answer=gen.text.strip(),
            sources=sources,
            finish_reason=gen.finish_reason,
            completion_tokens=gen.completion_tokens,
            max_tokens=gen.max_tokens,
        )
