import re
from collections.abc import AsyncIterator
from typing import Any

from src.core.ai.embeddings import OllamaEmbedder
from src.core.utils.datetime_utils import get_utc_now
from src.core.utils.uzbek_script import (
    StreamingTransliterator,
    is_cyrillic_text,
    to_cyrillic,
    to_latin,
)
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


# Savoldagi ism deb hisoblanmaydigan umumiy so'zlar (aks holda "raqami" kabi
# so'z tasodifan biror ismning boshiga mos kelib qolardi)
_QUERY_STOP = {
    "ip", "raqam", "raqami", "raqamlari", "raqamini", "nomer", "ichki",
    "xodim", "xodimi", "xodimlar", "xodimlari", "xodimning", "hodim",
    "telefon", "telefoni", "kim", "kimniki", "kimning", "qaysi", "qanday",
    "nima", "necha", "bering", "ber", "beray", "top", "toping", "kerak",
    "departament", "departamenti", "bolim", "bolimi", "bolimning",
    "boshqarma", "boshqarmasi", "lavozim", "lavozimi", "haqida", "bilan",
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

    # 3) Bo'lim nomi — FAQAT savolda aniq xodim-niyat (xodim/ip) bo'lsa. Aks holda
    # filial/manzil so'rovlari ("...bank xizmatlari markazi") xodim bo'limiga
    # noto'g'ri tushib ketardi. Ism qidiruvidan OLDIN turadi, chunki bo'lim nomi
    # tasodifan biror ismning boshiga o'xshab qolishi mumkin.
    if _has_employee_intent(q_lower):
        for dept in {str(e.get("department", "")) for e in emps}:
            distinctive = [
                t for t in _words(dept) if len(t) >= 2 and t not in _DEPT_STOP
            ]
            if distinctive and any(
                t in qwords or (len(t) >= 4 and t in q_lower) for t in distinctive
            ):
                return [e for e in emps if str(e.get("department", "")) == dept]

    # 4) F.I.SH — QISMAN moslash: savoldagi so'z ism/familiyaning boshiga mos
    # kelsa yetarli ("Shaxzod" -> "Shaxzodbek", "Jasur" -> "Jasurbek"). Eng ko'p
    # so'zi mos kelgan xodim(lar) qaytariladi — bir nechta bo'lsa hammasi, model
    # ularni ro'yxat qilib qaysi biri kerakligini so'raydi.
    qtokens = [
        t for t in _words(q_lower) if len(t) >= 3 and t not in _QUERY_STOP
    ]
    if not qtokens:
        return []
    scored: list[tuple[int, dict[str, Any]]] = []
    for e in emps:
        toks = [
            t
            for t in _words(str(e.get("fish", "")))
            if len(t) >= 3 and t not in _NAME_STOP
        ]
        score = 0
        for nt in toks:
            if any(nt.startswith(qt) or qt.startswith(nt) for qt in qtokens):
                score += 1
        if score:
            scored.append((score, e))
    if scored:
        best = max(s for s, _ in scored)
        return [e for s, e in scored if s == best]

    return []


# Foydalanuvchi ro'yxatdan faqat RAQAM yozib tanlashi mumkin ("53"). Bunda
# savolni oldingi javobdagi ro'yxatning o'sha bandi nomi bilan almashtiramiz —
# aks holda "53" embed qilinib, hech narsa topilmasdi.
_NUM_ONLY_RE = re.compile(r"^\s*(\d{1,3})\s*[.)]?\s*$")
_LIST_ITEM_RE = re.compile(r"^\s*(\d{1,3})\s*[.)]\s*(.+?)\s*$", re.MULTILINE)


# Ro'yxat bandlarida deyarli har doim uchraydigan, band nomini FARQLAMAYDIGAN
# so'zlar ("... Bank xizmatlari ofisi", "... krediti" kabi) — nomga mos
# kelish-kelmasligini tekshirganda e'tiborga olinmaydi.
_LIST_MATCH_STOPWORDS = {
    "bank", "xizmatlari", "markazi", "ofisi", "respublikasi", "viloyati",
    "shahar", "krediti", "kredit", "kartasi", "karta", "omonati", "omonat",
    "mikrokrediti", "mikroqarz", "ipoteka", "boyicha",
}


def _prefix_match(a: str, b: str) -> bool:
    """`a` va `b` boshidan qancha belgi bir xilligini tekshiradi — imlo farqi
    ("Yunusobod" / "Yunusubod") bo'lsa ham moslashtirish uchun. Qat'iy teng
    emas, lekin yetarlicha uzun umumiy prefiks talab qilinadi."""
    n = 0
    for ca, cb in zip(a, b):
        if ca != cb:
            break
        n += 1
    return n >= max(4, round(0.6 * min(len(a), len(b))))


def _resolve_list_choice(
    question: str, history: list[ChatTurn] | None
) -> str | None:
    """Oldingi javobdagi TANLOV RO'YXATIdan foydalanuvchi tanlagan bandning
    nomini qaytaradi (raqam yoki bandning o'zi nomi bilan yozilgan bo'lsa).
    Aks holda None.

    Eng oxirgi assistant javobi ro'yxat bo'lmasligi mumkin (foydalanuvchi avval
    bitta bandni tanlab javob olgan, keyin yana raqam yozadi) — shuning uchun
    orqaga qarab tanlov ro'yxatini qidiramiz. Mahsulot javobidagi qisqa
    "1-2-3 qadam" ro'yxatlari bilan chalkashmaslik uchun kamida 4 bandli
    ro'yxatni tanlov ro'yxati deb hisoblaymiz.

    MUHIM: bu funksiya "None emas" qaytarsa, chaqiruvchi xodim yo'nalishini
    SINAMAYDI — chunki bu ANIQ mahsulot ro'yxatidan tanlov ekani ma'lum
    (aks holda "Humo" yoki "Yunusobod" kabi nomlar tasodifan xodim ismiga
    o'xshab, noto'g'ri yo'nalib ketardi)."""
    if not history:
        return None
    num_match = _NUM_ONLY_RE.match(question)
    want_num = num_match.group(1) if num_match else None
    # MUHIM: savoldagi so'zlardan ham xuddi band matnidagidek umumiy so'zlar
    # olib tashlanadi — aks holda "markazi" (deyarli har bir bandda bor)
    # "market" so'ziga, "shahar" esa "Shahrisabz"ga tasodifan prefiks bo'yicha
    # mos kelib, butunlay boshqa band tanlanib qolardi.
    q_words = (
        []
        if want_num
        else [
            w for w in _words(to_latin(question))
            if len(w) >= 3 and w not in _LIST_MATCH_STOPWORDS
        ]
    )
    if want_num is None and not q_words:
        return None

    for turn in reversed(history):
        if turn.role != "assistant":
            continue
        items = _LIST_ITEM_RE.findall(turn.content)
        if len(items) < 4:
            continue  # tanlov ro'yxati emas (masalan javobdagi qadamlar)

        if want_num is not None:
            for num, text in items:
                if num == want_num:
                    cleaned = text.strip().strip("*").strip()
                    # Ro'yxat kirillcha ko'rsatilgan bo'lishi mumkin, baza esa
                    # LOTINCHA — nomni lotinga keltirmasak qidiruv hech narsa
                    # topmasdi ("15" -> "ma'lumotim yo'q" bo'lib qolardi).
                    return to_latin(cleaned) if cleaned else None
            return None  # tanlov ro'yxati topildi, unda bunday raqam yo'q

        # Raqam emas — bandning NOMI bilan yozgan bo'lishi mumkin. ENG YAXSHI
        # mos kelgan bandni tanlaymiz (birinchi mos kelganini emas) — aks
        # holda tasodifiy 1-so'zlik moslik (masalan boshqa bandning nomi)
        # haqiqiy tanlovdan OLDIN kelib qolsa, noto'g'ri band qaytardi.
        best: str | None = None
        best_hits = 0
        for _, text in items:
            cleaned = to_latin(text.strip().strip("*").strip())
            toks = [
                w for w in _words(cleaned)
                if len(w) >= 4 and w not in _LIST_MATCH_STOPWORDS
            ]
            if not toks:
                continue
            hits = sum(1 for t in toks if any(_prefix_match(t, qw) for qw in q_words))
            # Qisqa (1-2 so'zlik) nomda BARCHA so'z mos kelishi shart —
            # bitta tasodifiy prefiks moslikdan xato band tanlanmasin.
            need = len(toks) if len(toks) <= 2 else len(toks) - 1
            if hits >= need and hits > best_hits:
                best, best_hits = cleaned, hits
        return best
    return None


def _wants_cyrillic(question: str, history: list[ChatTurn] | None) -> bool:
    """Javobni kirillga o'girish kerakmi — foydalanuvchi kirillcha yozganmi
    shundan aniqlanadi. AI hamisha lotincha javob beradi (STRICT_RAG_SYSTEM),
    bu yerda esa kerak bo'lsa natijani foydalanuvchi kutgan alifboga o'giramiz.

    Savol faqat raqamdan iborat bo'lsa (ro'yxatdan tanlash, "3" kabi) — o'zida
    harf yo'q, shuning uchun suhbatdagi oxirgi matnli xabardan skriptni
    meros qilib olamiz (aks holda ro'yxatdan tanlagach javob "qaytib"
    lotinchaga o'tib qolardi)."""
    if is_cyrillic_text(question):
        return True
    if any(c.isalpha() for c in question):
        return False
    if not history:
        return False
    for turn in reversed(history):
        if turn.role == "user" and any(c.isalpha() for c in turn.content):
            return is_cyrillic_text(turn.content)
    return False


def _translit_preserving_titles(text: str, titles: list[str]) -> str:
    """Matnni kirillga o'giradi, lekin berilgan mahsulot NOMLARINI (Visa,
    MasterCard, UzCard kabi brend nomlari ham bo'ladi) lotincha holicha
    qoldiradi — ularni harf-baharf kirillga o'girish g'alati ko'rinardi."""
    ordered = sorted({t for t in titles if t}, key=len, reverse=True)
    masked = text
    placeholders: dict[str, str] = {}
    for i, title in enumerate(ordered):
        if title in masked:
            # Token faqat boshqaruv belgisi + raqamdan iborat — harf bo'lmasin,
            # aks holda to_cyrillic uni ham o'girib, tiklab bo'lmay qolardi.
            token = f"\x00{i}\x00"
            placeholders[token] = title
            masked = masked.replace(title, token)
    converted = to_cyrillic(masked)
    for token, title in placeholders.items():
        converted = converted.replace(token, title)
    return converted


# Saytdagi rasmiy nomlar foydalanuvchi ishlatadigan so'zdan farq qiladi
# (masalan "filial" so'zi bazada umuman yo'q — "bank xizmatlari markazi/ofisi"
# deb yozilgan). Embedding qidiruvi mos kelishi uchun savolni kengaytiramiz.
_QUERY_SYNONYMS: list[tuple[str, str]] = [
    ("filial", "bank xizmatlari markazi bank xizmatlari ofisi BXM"),
    ("bxm", "bank xizmatlari markazi"),
    ("bo'lim", "bank xizmatlari ofisi"),
    # "Bosh ofis" so'rovlari ko'pincha aniq manzil/xodim bo'laklarini emas,
    # umumiy "about" sahifasini topib, qisqa/noaniq javob berardi — bazadagi
    # aniq band nomini qo'shib, to'g'ri bo'lakka yo'naltiramiz.
    ("bosh ofis", "Toshkent shahar bank xizmatlari markazi Turonbank Bosh ofis"),
    ("bosh idora", "Toshkent shahar bank xizmatlari markazi Turonbank Bosh ofis"),
]


def _expand_query(question: str) -> str:
    """Qidiruv (embedding) uchun savolga rasmiy sinonimlarni qo'shadi.
    Foydalanuvchiga ko'rinadigan savol o'zgarmaydi."""
    q = question.lower()
    extra = [syn for key, syn in _QUERY_SYNONYMS if key in q]
    return f"{question} {' '.join(extra)}" if extra else question


def _has_employee_intent(q_lower: str) -> bool:
    """Savol aniq XODIMLAR haqidami — bo'lim bo'yicha yo'naltirishni faqat shunda
    yoqamiz. Aks holda "Toshkent shahar BANK xizmatlari markazi" kabi filial nomi
    xodim bo'limiga (masalan "Bank karta...") noto'g'ri tushib ketardi."""
    if "ip" in set(_words(q_lower)):
        return True
    return any(
        w in q_lower
        for w in ("xodim", "hodim", "ходим", "ichki raqam", "ички рақам")
    )


def _strip_stray_followup(text: str) -> str:
    """Aniq (bitta mahsulot) javobda "Batafsil:" havolasi bo'ladi. Model ba'zan
    bunday aniq javobga ham keraksiz "Shu turlardan qaysi biri..." savolini
    qo'shib qo'yadi — uni oxiridan olib tashlaymiz (ro'yxat javobiga tegmaymiz)."""
    if "batafsil:" not in text.lower():
        return text
    lines = text.rstrip().split("\n")
    while lines:
        low = lines[-1].lower().strip()
        if not low:
            lines.pop()
            continue
        if ("qaysi biri" in low or "qaysinisi" in low) and "beray" in low:
            lines.pop()
            continue
        break
    return "\n".join(lines).rstrip()


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

        uploaded_at = get_utc_now().isoformat()
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
                        "uploaded_at": uploaded_at,  # sana bo'yicha saralash uchun
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
                {
                    "chunks": 0,
                    "lang": str(payload.get("lang", "")),
                    "preview": "",
                    "uploaded_at": "",
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

        return [
            KnowledgeItem(
                title=title,
                chunks=data["chunks"],
                lang=data["lang"],
                preview=data["preview"],
                uploaded_at=data["uploaded_at"],
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


# Keng savolda TURKUMNI emas, savolning o'zini bildiruvchi so'zlar — turkum
# ichida qo'shimcha filtr ("Toshkentdagi filiallar") izlaganda hisobga
# olinmaydi, aks holda "turlari", "ro'yxati" kabi so'zlar filtr deb qabul
# qilinib, hech narsa topilmasdi.
_BROAD_QUESTION_STOPWORDS = {
    "turlari", "turlarini", "turi", "royxati", "royxatini", "ronxat",
    "qanday", "qaysi", "qanaqa", "nima", "necha", "bormi", "bor", "mavjud",
    "menga", "meni", "sizda", "bizda", "kerak", "korsat", "korsating",
    "ayting", "aytib", "bering", "ber", "beringchi", "hammasi", "hamma",
    "barcha", "butun", "yana", "haqida", "boyicha", "uchun", "bilan",
    "malumot", "malumotlar", "malumotlarini", "malumotini", "batafsil",
    "iltimos", "bank", "banki", "bankning", "turonbank", "turonbankning",
    "ochiq", "yaqin", "eng",
}


def _matches_filters(text: str, filters: list[str]) -> bool:
    """Mahsulot matni savoldagi qo'shimcha shart(lar)ga mos keladimi.

    So'z BOSHI bo'yicha solishtiriladi — o'zbekcha qo'shimchalar tufayli
    ("Toshkentdagi" -> "Toshkent", "Samarqanddagi" -> "Samarqand") aynan
    tenglik ishlamaydi. Bir nechta filtr bo'lsa, kamida bittasi mos kelishi
    yetarli (savolda odatda bitta hudud nomi bo'ladi, qolgani shovqin)."""
    words = set(_words(to_latin(text)))
    for f in filters:
        for w in words:
            if w.startswith(f) or f.startswith(w):
                # Juda qisqa umumiy bo'lakdan tasodifiy moslik bo'lmasin
                if min(len(w), len(f)) >= 4:
                    return True
    return False


# Turkum nomi (— _category_label qaytaradigan label bilan AYNAN mos kelishi
# shart) -> savolda uchrashi mumkin bo'lgan kalit so'zlar. _broad_category_reply
# shu asosida savol qaysi turkum haqida ekanini aniqlaydi.
_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Bank kartalari": ("karta",),
    "Kreditlar": ("kredit", "ipoteka", "qarz", "mikroqarz", "mikrokredit"),
    "Omonatlar": ("omonat", "depozit"),
    "Pul o'tkazmalari": ("o'tkazma", "otkazma", "o'tkazish", "otkazish"),
    "Filiallar (bank xizmatlari markazlari va ofislari)": (
        "filial",
        "bxm",
        "bank xizmatlari markazi",
        "bank xizmatlari ofisi",
    ),
}


class AnswerQuestionUseCase:
    """RAG: savolni embed qiladi, Qdrant'dan eng yaqin bo'laklarni topadi va
    ularni kontekst sifatida Qwen'ga berib javob oldiradi."""

    # Bitta mahsulotning bir necha bo'lagi bo'ladi (masalan omonatning aniq
    # shartlari alohida qisqa bo'lakda) — hammasi tushishi uchun yetarlicha keng.
    TOP_K = 8
    TEMPERATURE = 0.2
    # Javob yozish vaqti taxminan token soniga proporsional — sekin hardware'da
    # cheklovni pasaytirsak eng yomon holatdagi kutish qisqaradi. Javoblar odatda
    # 500 tokendan qisqa, shuning uchun 1024 yetarli.
    MAX_TOKENS = 2048
    HISTORY_LIMIT = 6  # oxirgi shuncha xabar (promptni yengil tutish uchun)
    # Eng yaqin bo'lakning cosine o'xshashligi shundan past bo'lsa — savol bazaga
    # aloqasiz (bema'ni yoki mavzudan tashqari) deb hisoblaymiz va LLM'ni umuman
    # chaqirmasdan tayyor "ma'lumotim yo'q" javobini qaytaramiz (tez javob uchun).
    #
    # PAST chegara ATAYIN: avval 0.35 edi va bu erkin yozilgan (tugma orqali
    # emas) savollarning ko'pini LLM'ga yetib bormasdan turib rad etardi —
    # foydalanuvchi "faqat tugmalar ishlayapti" deb shikoyat qilgan sabab shu.
    # Endi faqat CHINDAN aloqasiz (bema'ni) savol kesiladi; qolganida
    # kontekst LLM'ga beriladi va u yetarli ma'lumot yo'qligini o'zi aytadi.
    MIN_SCORE = 0.15

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
    def _category_label(source_url: str, title: str = "") -> str:
        """Mahsulot turkumini aniqlaydi — katalogni guruhlash uchun
        (kartalar / kreditlar / omonatlar / filiallar ...)."""
        # Filiallar saytda "filial" deb emas, "bank xizmatlari markazi/ofisi"
        # deb nomlangan — turkumni SARLAVHA bo'yicha aniqlaymiz.
        t = title.lower()
        if "bank xizmatlari markazi" in t or "bank xizmatlari ofisi" in t:
            return "Filiallar (bank xizmatlari markazlari va ofislari)"
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

    async def _catalog_groups(self) -> dict[str, list[str]]:
        """Bazadagi BARCHA mahsulotlarning to'liq ro'yxati (title bo'yicha noyob),
        turkumlarga ajratilgan (faqat nomlar, URL'siz). _build_catalog (LLM uchun
        matn) va _broad_category_reply (keng savolga deterministik javob) shu
        yerdan foydalanadi."""
        detailed = await self._catalog_groups_detailed()
        return {cat: [t for t, _ in items] for cat, items in detailed.items()}

    async def _catalog_groups_detailed(self) -> dict[str, list[tuple[str, str]]]:
        """_catalog_groups bilan bir xil, lekin har bir mahsulot uchun uning
        BUTUN matni ham qaytariladi: (nom, to'liq matn).

        Matn kerak, chunki foydalanuvchi turkum ichida QO'SHIMCHA shart bilan
        so'rashi mumkin ("Toshkentdagi filiallar") — manzil/hudud faqat
        mahsulot matnida bo'ladi, nomida emas."""
        payloads = await self.store.scroll_all(limit=2000)
        # title bo'yicha noyob mahsulotlar (birinchi uchragan source_url bilan).
        # Xodimlar (doc_type=employee) mahsulot katalogiga kirmaydi.
        urls: dict[str, str] = {}
        texts: dict[str, list[str]] = {}
        for p in payloads:
            if p.get("doc_type") == "employee":
                continue
            title = str(p.get("title", "")).strip()
            if not title:
                continue
            urls.setdefault(title, str(p.get("source_url", "")))
            # Bitta mahsulot bir necha bo'lakdan iborat — hammasini yig'amiz,
            # manzil qaysi bo'lakda bo'lishidan qat'i nazar topilsin.
            texts.setdefault(title, []).append(str(p.get("chunk_text", "")))

        groups: dict[str, list[tuple[str, str]]] = {}
        for title, url in urls.items():
            label = self._category_label(url, title)
            groups.setdefault(label, []).append((title, " ".join(texts[title])))
        return groups

    async def _build_catalog(self) -> str:
        """Semantik qidiruv faqat eng yaqin bir nechtasini topadi — bu esa keng
        savolga ("barcha kredit turlari") TO'LIQ javob berish uchun butun
        katalogni matn ko'rinishida beradi."""
        groups = await self._catalog_groups()
        if not groups:
            return ""
        blocks = [
            f"### {cat}\n" + "\n".join(f"- {t}" for t in items)
            for cat, items in groups.items()
        ]
        return "\n\n".join(blocks)

    async def _broad_category_reply(
        self, question: str, want_cyrillic: bool
    ) -> str | None:
        """Savol aniq bir mahsulotni emas, balki butun turkumni so'rasa (masalan
        "omonatlar", "kredit turlari") — nomlarni katalogdan DETERMINISTIK
        tarzda, LLM'ni chaqirmasdan, raqamlangan ro'yxat qilib qaytaradi.

        LLM'ga qoldirilganda format izchil bo'lmay qolgan (masalan "Omonatlar"
        uchun ba'zan vergul bilan sanab o'tish, ba'zan raqamlangan ro'yxat
        chiqib turgan) — bu yerda natijani kodning o'zi kafolatlaydi. Bunga
        qo'shimcha: keyingi "3-bandni tanladim" javobi ham FAQAT raqamlangan
        "N. nom" formatidan ishlaydi (_resolve_list_choice), shuning uchun
        format barqarorligi funksional jihatdan ham muhim.

        Mahsulot NOMLARI (Visa, MasterCard, UzCard kabi brend nomlari ham bor)
        kirillcha bo'lsa ham HAR DOIM lotincha qoladi — ularni harf-baharf
        kirillga o'girish g'alati ko'rinardi; faqat atrofidagi savol matni
        o'giriladi."""
        groups = await self._catalog_groups_detailed()
        if not groups:
            return None

        # Turkum kalit so'zlari va mahsulot nomlari LOTINCHA — savol kirillcha
        # yozilgan bo'lsa ("Кредит турлари") lotinga keltiramiz, aks holda
        # hech biri mos kelmay, ro'yxat o'rniga LLM javob berib qolardi.
        q = to_latin(question).lower()

        # Savolda aniq mahsulot nomi tilga olingan bo'lsa — bu keng savol emas,
        # LLM aniq javob bersin deb oddiy RAG yo'liga qoldiramiz.
        for items in groups.values():
            for title, _ in items:
                toks = [t for t in _words(title) if len(t) >= 4]
                if toks and all(t in q for t in toks[: min(2, len(toks))]):
                    return None

        for label, keywords in _CATEGORY_KEYWORDS.items():
            items = groups.get(label)
            if not items or not any(kw in q for kw in keywords):
                continue

            # Turkum ichida QO'SHIMCHA shart bormi ("Toshkentdagi filiallar",
            # "Samarqand BXM") — savoldan turkum/savol so'zlarini olib
            # tashlagach qolgan so'zlar bo'yicha filtrlaymiz. Manzil mahsulot
            # NOMIDA emas, MATNIDA bo'lgani uchun matn bo'yicha qidiriladi.
            filters = [
                w for w in _words(q)
                if len(w) >= 4
                and w not in _BROAD_QUESTION_STOPWORDS
                and not any(w.startswith(kw) or kw.startswith(w) for kw in keywords)
            ]
            shown = items
            note = ""
            if filters:
                matched = [
                    (title, text) for title, text in items
                    if _matches_filters(f"{title} {text}", filters)
                ]
                # Faqat haqiqiy toraytirish bo'lsa qo'llaymiz: hech narsa
                # topilmasa yoki hammasi mos kelsa — to'liq ro'yxat qaytadi.
                if matched and len(matched) < len(items):
                    shown = matched
                    note = f"\"{' '.join(filters)}\" bo'yicha topilganlar:\n\n"

            numbered = "\n".join(f"{i}. {t}" for i, (t, _) in enumerate(shown, 1))
            closing = (
                "Shu turlardan qaysi biri bo'yicha batafsil ma'lumot beray? "
                "Nomini yoki tartib raqamini yozing."
            )
            if want_cyrillic:
                closing = to_cyrillic(closing)
                note = to_cyrillic(note)
            return f"{note}{numbered}\n\n{closing}"
        return None

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
        # Javobni kirillga o'girish kerakmi — savol (raqamga almashtirilishidan
        # OLDIN) qaysi alifboda yozilganiga qarab. AI hamisha lotincha yozadi
        # (STRICT_RAG_SYSTEM), foydalanuvchi kirillcha yozgan bo'lsa shu yerda
        # javobni uning alifbosiga o'giramiz.
        want_cyrillic = _wants_cyrillic(question, history)

        # Ichki barcha mantiq (xodim qidiruvi, turkum kalit so'zlari, embedding
        # qidiruvi, baza) LOTINCHA ishlaydi — savolni shu yerdayoq lotinga
        # keltiramiz. Aks holda kirillcha savol embedding'ga kirillcha
        # ketib, mos kontekst topilmay "ma'lumotim yo'q" qaytardi.
        question = to_latin(question)

        # Foydalanuvchi ro'yxatdan raqam bilan tanlagan bo'lsa ("53") — savolni
        # o'sha band nomiga almashtiramiz (qidiruv ham, prompt ham shuni ko'radi).
        # Bu MAHSULOT ro'yxatidan tanlov ekani ANIQ — shuning uchun xodim
        # yo'nalishini SINAMAYMIZ ham (aks holda "Humo" kabi mahsulot nomi
        # "Humoyun" degan xodimga tasodifan mos kelib, noto'g'ri yo'nalardi).
        resolved = _resolve_list_choice(question, history)
        question = resolved or question

        # Xodim (telefon/IP) savoli — alohida yo'l (mahsulot RAG'siz)
        route = None if resolved else await self._employee_route(question)
        if route is not None:
            kind, emps = route
            if kind == "ask":
                text = to_cyrillic(EMPLOYEE_ASK_REPLY) if want_cyrillic else EMPLOYEE_ASK_REPLY
                yield {"type": "delta", "text": text}
                yield {
                    "type": "done",
                    "completion_tokens": 0,
                    "finish_reason": "stop",
                    "max_tokens": self.MAX_TOKENS,
                    "sources": [],
                }
                return
            emp_prompt = self._employee_prompt(question, history, emps)
            tr = StreamingTransliterator() if want_cyrillic else None
            async for ev in self.ai_client.stream_generate(
                emp_prompt,
                system_prompt=EMPLOYEE_SYSTEM,
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS,
            ):
                if tr is not None and ev.get("type") == "delta":
                    ev = {**ev, "text": tr.feed(ev["text"])}
                if ev.get("type") == "done":
                    if tr is not None and (rest := tr.flush()):
                        yield {"type": "delta", "text": rest}
                    ev["max_tokens"] = self.MAX_TOKENS
                    ev["sources"] = []
                yield ev
            return

        # Turkumning BARCHA mahsulotini so'ragan keng savol — LLM'ni chaqirmasdan,
        # katalogdan deterministik raqamlangan ro'yxat qaytaramiz (format har doim
        # bir xil bo'lsin: LLM'ga qoldirilsa ba'zan vergul bilan ham chiqib turardi).
        broad_reply = await self._broad_category_reply(question, want_cyrillic)
        if broad_reply is not None:
            yield {"type": "delta", "text": broad_reply}
            yield {
                "type": "done",
                "completion_tokens": 0,
                "finish_reason": "stop",
                "max_tokens": self.MAX_TOKENS,
                "sources": [],
            }
            return

        # Qidiruvda rasmiy sinonimlar bilan kengaytiramiz ("filial" -> "bank
        # xizmatlari markazi/ofisi"), promptdagi SAVOL esa asl holicha qoladi.
        query_vector = await self.embedder.embed(_expand_query(question))
        results = await self.store.search(query_vector, top_k=self.TOP_K)

        top_score = results[0][1] if results else 0.0
        if not results or top_score < self.MIN_SCORE:
            text = to_cyrillic(NO_INFO_REPLY) if want_cyrillic else NO_INFO_REPLY
            yield {"type": "delta", "text": text}
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
        tr = StreamingTransliterator() if want_cyrillic else None
        async for ev in self.ai_client.stream_generate(
            prompt,
            system_prompt=STRICT_RAG_SYSTEM,
            temperature=self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS,
        ):
            if tr is not None and ev.get("type") == "delta":
                ev = {**ev, "text": tr.feed(ev["text"])}
            if ev.get("type") == "done":
                if tr is not None and (rest := tr.flush()):
                    yield {"type": "delta", "text": rest}
                ev["max_tokens"] = self.MAX_TOKENS
                ev["sources"] = src_dump
            yield ev

    async def execute(
        self, question: str, history: list[ChatTurn] | None = None
    ) -> AnswerResult:
        # Javobni kirillga o'girish kerakmi — savol (raqamga almashtirilishidan
        # OLDIN) qaysi alifboda yozilganiga qarab.
        want_cyrillic = _wants_cyrillic(question, history)

        # Ichki barcha mantiq (xodim qidiruvi, turkum kalit so'zlari, embedding
        # qidiruvi, baza) LOTINCHA ishlaydi — savolni shu yerdayoq lotinga
        # keltiramiz. Aks holda kirillcha savol embedding'ga kirillcha
        # ketib, mos kontekst topilmay "ma'lumotim yo'q" qaytardi.
        question = to_latin(question)

        # Foydalanuvchi ro'yxatdan raqam bilan tanlagan bo'lsa ("53") — savolni
        # o'sha band nomiga almashtiramiz (qidiruv ham, prompt ham shuni ko'radi).
        # Bu MAHSULOT ro'yxatidan tanlov ekani ANIQ bo'lsa, xodim yo'nalishini
        # sinamaymiz ham (aks holda "Humo" kabi mahsulot nomi "Humoyun" degan
        # xodimga tasodifan mos kelib, noto'g'ri yo'nalardi).
        resolved = _resolve_list_choice(question, history)
        question = resolved or question

        # Xodim (telefon/IP) savoli — alohida yo'l (mahsulot RAG'siz)
        route = None if resolved else await self._employee_route(question)
        if route is not None:
            kind, emps = route
            if kind == "ask":
                answer = to_cyrillic(EMPLOYEE_ASK_REPLY) if want_cyrillic else EMPLOYEE_ASK_REPLY
                return AnswerResult(
                    answer=answer,
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
            answer = gen.text.strip()
            return AnswerResult(
                answer=to_cyrillic(answer) if want_cyrillic else answer,
                sources=[],
                finish_reason=gen.finish_reason,
                completion_tokens=gen.completion_tokens,
                max_tokens=gen.max_tokens,
            )

        # Turkumning BARCHA mahsulotini so'ragan keng savol — LLM'ni chaqirmasdan,
        # katalogdan deterministik raqamlangan ro'yxat qaytaramiz (format har doim
        # bir xil bo'lsin: LLM'ga qoldirilsa ba'zan vergul bilan ham chiqib turardi).
        broad_reply = await self._broad_category_reply(question, want_cyrillic)
        if broad_reply is not None:
            return AnswerResult(
                answer=broad_reply,
                sources=[],
                finish_reason="stop",
                completion_tokens=0,
                max_tokens=self.MAX_TOKENS,
            )

        # Qidiruvda rasmiy sinonimlar bilan kengaytiramiz ("filial" -> "bank
        # xizmatlari markazi/ofisi"), promptdagi SAVOL esa asl holicha qoladi.
        query_vector = await self.embedder.embed(_expand_query(question))
        results = await self.store.search(query_vector, top_k=self.TOP_K)

        # Mos kontekst yo'q (yoki eng yaqini ham juda uzoq) — LLM'ni chaqirmasdan
        # darrov "ma'lumotim yo'q" deb qaytaramiz. Bu bema'ni/aloqasiz savolga
        # modelning uzoq (bir necha daqiqa) "o'ylab" javob berishini oldini oladi.
        top_score = results[0][1] if results else 0.0
        if not results or top_score < self.MIN_SCORE:
            return AnswerResult(
                answer=to_cyrillic(NO_INFO_REPLY) if want_cyrillic else NO_INFO_REPLY,
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

        answer = _strip_stray_followup(gen.text.strip())
        if want_cyrillic:
            answer = _translit_preserving_titles(answer, [s.title for s in sources])
        return AnswerResult(
            answer=answer,
            sources=sources,
            finish_reason=gen.finish_reason,
            completion_tokens=gen.completion_tokens,
            max_tokens=gen.max_tokens,
        )
