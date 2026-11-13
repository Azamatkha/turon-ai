"""Bilim bazasiga YOZISH va boshqarish usecase'lari (yuklash, PDF,
xodimlar, scraping, ro'yxat/tahrir/o'chirish).

`usecases.py` dan ko'chirilgan — mantiq o'zgarmagan, faqat joyi.
"""

from datetime import date
from typing import Any

from anyio import to_thread

from loggers import get_logger
from src.core.ai.embeddings import OllamaEmbedder
from src.core.ai.interfaces import BaseAIClient
from src.core.errors.exceptions import (
    InfrastructureException,
    InstanceNotFoundException,
    InstanceProcessingException,
)
from src.core.utils.datetime_utils import get_utc_now
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge.chunking import chunk_text
from src.knowledge.employee_parser import parse_employees
from src.knowledge.pdf_extractor import (
    extract_pdf_text,
    join_pages,
    page_fallback_text,
    render_pdf_pages,
)
from src.knowledge.prompts import (
    PDF_CLEAN_SYSTEM,
    PDF_TITLE_SYSTEM,
    PDF_VISION_SYSTEM,
)
from src.knowledge.rescrape import find_duplicates, group_by_title
from src.knowledge.schemas import (
    KnowledgeChunk,
    KnowledgeDetail,
    KnowledgeItem,
    PdfUploadResult,
    UploadResult,
)
from src.knowledge.scraper import extract_content, fetch_html

logger = get_logger(__name__)

class UploadKnowledgeUseCase:
    def __init__(self, embedder: OllamaEmbedder, store: QdrantStore) -> None:
        self.embedder = embedder
        self.store = store

    async def execute(
        self,
        title: str,
        text: str,
        source_url: str = "",
        extra_payload: dict[str, Any] | None = None,
    ) -> UploadResult:
        """`extra_payload` — har bir bo'lak payload'iga qo'shiladigan qo'shimcha
        maydonlar. Valyuta kurslari uchun ishlatiladi: matn bilan bir qatorda
        STRUKTURALI JSON ham saqlanadi, shunda oyna (modal) uchun alohida baza
        yoki jadval kerak bo'lmaydi."""
        chunks = chunk_text(text)
        if not chunks:
            raise InstanceProcessingException("Matn bo'sh — yozadigan narsa yo'q")

        uploaded_at = get_utc_now().isoformat()
        vectors: list[list[float]] = []
        payloads: list[dict[str, Any]] = []
        try:
            for index, chunk in enumerate(chunks):
                # Sarlavhani faqat EMBEDDING uchun bo'lakka qo'shamiz (kontekst
                # kuchayadi, bo'lak boshqa mahsulotnikiga aralashmaydi), lekin
                # SAQLANADIGAN chunk_text'ga QO'SHMAYMIZ — aks holda:
                #  1) admin detali/tahrir oynasida sarlavha har bo'lakda takrorlanib
                #     ko'rinardi;
                #  2) tahrirlab qayta saqlaganda sarlavha matn ichiga kirib, keyingi
                #     saqlashda yana qo'shilib, to'planib borardi.
                # Javob promptida mahsulot nomi baribir "[title]" sarlavhasi bilan
                # beriladi (_assemble), shuning uchun kontekst yo'qolmaydi.
                payload: dict[str, Any] = {
                    "title": title,
                    "chunk_text": chunk,
                    "chunk_index": index,
                    "lang": "uz",
                    "source_url": source_url,  # manba havolasi (parsing uchun)
                    "uploaded_at": uploaded_at,  # sana bo'yicha saralash uchun
                }
                if extra_payload:
                    payload.update(extra_payload)
                payloads.append(payload)
            vectors = await self.embedder.embed_many(
                [f"{title}\n\n{chunk}" for chunk in chunks]
            )
        except Exception as exc:
            raise InfrastructureException(
                f"Embedding xizmati bilan bog'lanib bo'lmadi: {type(exc).__name__}: {exc!r}"
            ) from exc

        try:
            dim = len(vectors[0])
            await self.store.ensure_collection(dim)
            await self.store.upsert(vectors, payloads)
            # Yangi matn qisqaroq bo'lsa, eski matnning ortiqcha bo'laklari qolmasin
            await self.store.delete_stale_chunks(title, keep=len(chunks))
            total = await self.store.count()
        except Exception as exc:
            raise InfrastructureException(
                f"Vektor bazasi (Qdrant) bilan bog'lanib bo'lmadi: {type(exc).__name__}: {exc!r}"
            ) from exc
        return UploadResult(chunks=len(chunks), vector_dim=dim, total_points=total)


class UploadPdfUseCase:
    """PDF (ko'pincha skanerlangan ichki hujjat) -> matn -> LLM tozalash ->
    Qdrant.

    Uch bosqich:
    1) pdf_extractor: matn qatlami bo'lsa o'qiydi, bo'lmasa sahifani OCR qiladi;
    2) LLM har bo'lakdan imzo/muhr/OCR shovqinini olib tashlaydi (mazmunni
       QISQARTIRMASDAN);
    3) odatdagi UploadKnowledgeUseCase — chunk + embed + yozish.

    Sarlavha berilmasa — LLM matnning boshidan hujjat mavzusini aniqlaydi."""

    # LLM'ga bir marta beriladigan bo'lak kattaligi. Katta bo'lak = kam chaqiruv,
    # lekin sekin hardware'da bitta chaqiruv juda uzoq davom etadi va model
    # oxirini kesib qo'yishi mumkin — shuning uchun o'rtacha o'lcham.
    CLEAN_BLOCK_CHARS = 4000
    CLEAN_MAX_TOKENS = 3000
    # Ichki hujjatning rasmiy nomi uzun bo'ladi ("... tizimida kredit va unga
    # tenglashtirilgan aktivlar bo'yicha monitoring o'tkazish tartibi") — qisqa
    # cheklov uni o'rtasidan kesib qo'yardi.
    TITLE_MAX_TOKENS = 128
    TEMPERATURE = 0.1
    # Rasmiy nom ko'pincha muqova/1-sahifada, "TASDIQLANGAN" muhridan keyin
    # keladi — namuna yetarlicha uzun bo'lishi kerak.
    TITLE_SAMPLE_CHARS = 3000
    # Tozalangan bo'lak asl bo'lakning shuncha ulushidan qisqa bo'lsa — model
    # tozalash o'rniga qisqartirib (yoki javob bermay) qo'ygan deb hisoblab,
    # ASL matnni saqlaymiz: mazmun yo'qolgandan ko'ra shovqin qolgani yaxshi.
    MIN_KEEP_RATIO = 0.4

    def __init__(
        self,
        embedder: OllamaEmbedder,
        store: QdrantStore,
        ai_client: BaseAIClient,
    ) -> None:
        self.embedder = embedder
        self.store = store
        self.ai_client = ai_client

    async def _clean(self, text: str) -> str:
        """Matnni bo'lak-bo'lak LLM'dan o'tkazib tozalaydi."""
        blocks = chunk_text(
            text, max_chars=self.CLEAN_BLOCK_CHARS, min_chars=self.CLEAN_BLOCK_CHARS // 4
        )
        cleaned: list[str] = []
        for block in blocks:
            try:
                out = await self.ai_client.generate_text(
                    block,
                    system_prompt=PDF_CLEAN_SYSTEM,
                    temperature=self.TEMPERATURE,
                    max_tokens=self.CLEAN_MAX_TOKENS,
                )
            except Exception:
                # Model javob bermasa hujjat butunlay yo'qolmasin — asl bo'lak
                cleaned.append(block)
                continue
            out = out.strip()
            if not out:
                continue  # butunlay imzo/muhr sahifasi — tashlab yuboriladi
            if len(out) < len(block) * self.MIN_KEEP_RATIO:
                out = block
            cleaned.append(out)
        return "\n\n".join(cleaned).strip()

    async def _guess_title(self, text: str) -> str:
        try:
            raw = await self.ai_client.generate_text(
                text[: self.TITLE_SAMPLE_CHARS],
                system_prompt=PDF_TITLE_SYSTEM,
                temperature=0.3,
                max_tokens=self.TITLE_MAX_TOKENS,
            )
        except Exception:
            return ""
        return raw.strip().strip('"').strip("'").strip()[:200]

    # Bitta sahifa uchun model javobi chegarasi (zich jadvalli sahifa ham sig'adi)
    VISION_PAGE_MAX_TOKENS = 4096
    # Bitta sahifani o'qish vaqti chegarasi (soniya)
    VISION_PAGE_TIMEOUT = 180.0

    async def _read_with_vision(self, file_bytes: bytes) -> tuple[str, int, int, int]:
        """Har sahifani RASM qilib modelga o'qitadi.

        Qaytaradi: (matn, sahifalar, OCR/zaxira sahifalar, model o'qigan sahifalar).
        Model biror sahifada yiqilsa (timeout, xato) — o'sha sahifa uchun eski
        yo'l: matn qatlami, u bo'lmasa OCR. Hujjat bitta sahifa tufayli
        butunlay yo'qolmasin."""
        pages = await to_thread.run_sync(render_pdf_pages, file_bytes)
        parts: list[str] = []
        vision_pages = 0
        fallback_pages = 0
        for i, page in enumerate(pages, start=1):
            try:
                res = await self.ai_client.read_image(
                    page.png,
                    prompt="Transcribe this page.",
                    system_prompt=PDF_VISION_SYSTEM,
                    max_tokens=self.VISION_PAGE_MAX_TOKENS,
                    timeout=self.VISION_PAGE_TIMEOUT,
                )
                parts.append(res.text.strip())
                vision_pages += 1
            except Exception as exc:
                logger.warning(
                    "[PDF] %d-sahifani model o'qiy olmadi (%s) — matn qatlami/OCR",
                    i, type(exc).__name__,
                )
                parts.append(await to_thread.run_sync(page_fallback_text, page))
                fallback_pages += 1
        logger.info(
            "[PDF] %d sahifa: model %d ta, zaxira %d ta", len(pages), vision_pages, fallback_pages
        )
        return join_pages(parts), len(pages), fallback_pages, vision_pages

    async def execute(
        self, file_bytes: bytes, filename: str, title: str = ""
    ) -> PdfUploadResult:
        vision_pages = 0
        if await self.ai_client.supports_vision():
            # Model sahifani o'zi "ko'rib" o'qiydi: imzo/muhrni o'zi tashlaydi,
            # shuning uchun alohida LLM tozalash bosqichi kerak emas.
            raw_text, pages, ocr_pages, vision_pages = await self._read_with_vision(
                file_bytes
            )
        else:
            raw_text, pages, ocr_pages = extract_pdf_text(file_bytes)
        if not raw_text:
            raise InstanceProcessingException(
                "PDF'dan matn ajratib bo'lmadi — sahifalar bo'sh yoki skan "
                "sifati juda past. Faylni yaxshiroq sifatda skanerlab ko'ring."
            )

        cleaned = raw_text if vision_pages else await self._clean(raw_text)
        if not cleaned:
            raise InstanceProcessingException(
                "Hujjatda mazmunli matn topilmadi (faqat imzo/muhr sahifalari?)."
            )

        final_title = title.strip() or await self._guess_title(cleaned)
        if not final_title:
            # Zaxira: fayl nomi (kengaytmasiz)
            final_title = filename.rsplit(".", 1)[0].strip() or "Hujjat"

        # Bir xil hujjat qayta yuklansa — eski bo'laklar qolib ketmasin
        await self.store.delete_by_title(final_title)
        result = await UploadKnowledgeUseCase(
            embedder=self.embedder, store=self.store
        ).execute(title=final_title, text=cleaned)
        return PdfUploadResult(
            chunks=result.chunks,
            vector_dim=result.vector_dim,
            total_points=result.total_points,
            title=final_title,
            pages=pages,
            ocr_pages=ocr_pages,
            vision_pages=vision_pages,
            chars=len(cleaned),
        )


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
            vectors = await self.embedder.embed_many(
                [str(p["chunk_text"]) for p in payloads]
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
            existing = await self.store.scroll_all_records()
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
        # Amal qilish muddati (admin qo'ygan) qayta yuklashda saqlanadi.
        _, valid_until = await UpdateKnowledgeUseCase(
            embedder=self.embedder, store=self.store
        )._existing_meta(title)
        await self.store.delete_by_title(title)
        return await UploadKnowledgeUseCase(
            embedder=self.embedder, store=self.store
        ).execute(
            title=title,
            text=text,
            source_url=url,
            extra_payload={"valid_until": valid_until} if valid_until else None,
        )

    async def _unique_title(self, title: str, url: str) -> str:
        """Boshqa (turli source_url'ga tegishli) yozuv bilan sarlavha
        to'qnashsa — ustidan bosib o'chirib yubormaslik uchun sarlavhani
        havola oxiridan ajratma qo'shib farqlaymiz."""
        if not await self.store.exists():
            return title
        payloads = await self.store.scroll_all_pages()
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

        payloads = await self.store.scroll_all_pages()

        # Sarlavha bo'yicha guruhlaymiz: har sarlavha ostida nechta bo'lak bor
        grouped: dict[str, dict[str, Any]] = {}
        for payload in payloads:
            title = str(payload.get("title", ""))
            group = grouped.setdefault(
                title,
                {
                    "chunks": 0,
                    "lang": str(payload.get("lang", "")),
                    "preview": "",
                    "uploaded_at": "",
                    "valid_until": "",
                },
            )
            group["chunks"] += 1
            # Birinchi bo'lak (chunk_index == 0) matnidan qisqa ko'rinish olamiz
            if payload.get("chunk_index") == 0:
                group["preview"] = str(payload.get("chunk_text", ""))[:160]
            # Sana — eng kechki bo'lak vaqti (eski yozuvlarda bo'lmasligi mumkin)
            at = str(payload.get("uploaded_at", ""))
            if at > str(group["uploaded_at"]):
                group["uploaded_at"] = at
            if payload.get("valid_until") and not group["valid_until"]:
                group["valid_until"] = str(payload["valid_until"])[:10]

        # Matni AYNAN bir xil hujjatlar (bir sahifa ikki marta turli sarlavha
        # bilan yuklangan) — botga bir xil kontekst ikki marta tushadi
        duplicates = find_duplicates(group_by_title(payloads))
        return [
            KnowledgeItem(
                title=title,
                chunks=data["chunks"],
                lang=data["lang"],
                preview=data["preview"],
                uploaded_at=data["uploaded_at"],
                valid_until=data["valid_until"],
                duplicates=duplicates.get(title, []),
            )
            for title, data in grouped.items()
        ]


class GetKnowledgeDetailUseCase:
    def __init__(self, store: QdrantStore) -> None:
        self.store = store

    async def execute(self, title: str) -> KnowledgeDetail:
        if not await self.store.exists():
            raise InstanceNotFoundException("Ma'lumot topilmadi")

        payloads = await self.store.scroll_all_pages()
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
        # HAVOLA SAQLANADI. Ilgari tahrirlangan yozuv `source_url`siz qayta
        # yozilardi va bu ikki narsani buzardi:
        #  1) turkum aynan havoladan aniqlanadi (`_category_label`) — havolasiz
        #     yozuv "Boshqa xizmatlar"ga tushib, "Omonatlar" ro'yxatidan
        #     yo'qolardi (sarlavhasi tahrirlangan «Meros» shunday yo'qolgan);
        #  2) javob oxiridagi "Batafsil: <havola>" qatori ham chiqmay qolardi.
        # Amal qilish muddati ham saqlanadi — tahrir uni o'chirib yubormasin
        source_url, valid_until = await self._existing_meta(old_title)
        await self.store.delete_by_title(old_title)
        return await UploadKnowledgeUseCase(
            embedder=self.embedder, store=self.store
        ).execute(
            title=title,
            text=text,
            source_url=source_url,
            extra_payload={"valid_until": valid_until} if valid_until else None,
        )

    async def _existing_meta(self, old_title: str) -> tuple[str, str]:
        """Tahrirlanayotgan yozuvning (havolasi, valid_until) — bo'lmasa bo'sh."""
        if not await self.store.exists():
            return "", ""
        source_url = valid_until = ""
        for payload in await self.store.scroll_all_pages():
            if str(payload.get("title", "")) != old_title:
                continue
            source_url = source_url or str(payload.get("source_url") or "")
            valid_until = valid_until or str(payload.get("valid_until") or "")
        return source_url, valid_until


class SetKnowledgeValidityUseCase:
    """Hujjatning amal qilish muddatini o'rnatadi yoki olib tashlaydi."""

    def __init__(self, store: QdrantStore) -> None:
        self.store = store

    async def execute(self, title: str, valid_until: date | None) -> None:
        if not await self.store.search_by_field("title", title, limit=1):
            raise InstanceNotFoundException("Ma'lumot topilmadi")
        await self.store.set_payload_by_title(
            title, {"valid_until": valid_until.isoformat() if valid_until else None}
        )
