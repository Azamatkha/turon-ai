"""Bilim bazasi turkumlari — bot uchun (katalog va keng savollar).

Turkumlarni ADMIN boshqaradi (kb_categories jadvali). Avtomatik taxmin yo'q:
hujjat qaysi turkumda ekanini faqat payload'dagi `category` kaliti aytadi.

Bot har savolda turkumlarga qaraydi, shuning uchun ro'yxat qisqa muddat
xotirada saqlanadi; admin o'zgartirganda kesh darhol tozalanadi.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import time

from loggers import get_logger
from src.core.database.session import async_session
from src.core.utils.uzbek_script import to_cyrillic, to_latin
from src.knowledge.models import KbCategory
from src.knowledge.repositories import KbCategoryRepository

logger = get_logger(__name__)

# Filiallar turkumi — unda ro'yxat HUDUD bo'yicha toraytiriladi (_branch_reply).
BRANCH_KEY = "branch"
# Turkumi qo'yilmagan hujjatlar katalogda shu nom ostida turadi.
UNCATEGORIZED_LABEL = "Boshqa xizmatlar"

# Turkumning O'ZINI bildiruvchi so'zlar: turkum ichida toraytirishda hisobga
# olinmaydi. Kalit so'zlardan FARQI: "ipoteka" kreditlar turkumini topadi,
# lekin u kredit TURI — ya'ni haqiqiy filtr ("Ipoteka kreditlari" so'roviga
# barcha 20 ta kredit emas, faqat ipotekalar). Faqat eski turkumlar uchun;
# admin yaratgan turkumda bu vazifani uning kalit so'zlari bajaradi.
_BUILTIN_GENERIC: dict[str, tuple[str, ...]] = {
    "card": ("karta",),
    "credit": ("kredit",),
    "deposit": ("omonat", "depozit"),
    "transfer": ("otkazma", "otkazish"),
}

# Baza ishlamay qolsa (yoki testda) — migratsiya seed qilgan turkumlar.
_DEFAULTS: list[tuple[str, str, str]] = [
    ("card", "Bank kartalari", "karta"),
    ("credit", "Kreditlar", "kredit, ipoteka, qarz, mikroqarz, mikrokredit"),
    ("deposit", "Omonatlar", "omonat, depozit"),
    ("transfer", "Pul o'tkazmalari", "o'tkazma, otkazma, o'tkazish, otkazish"),
    (
        "branch",
        "Filiallar (bank xizmatlari markazlari va ofislari)",
        "filial, bxm, bank xizmatlari markazi, bank xizmatlari ofisi",
    ),
    ("other", "Boshqa xizmatlar", ""),
]


def _norm(word: str) -> str:
    """Savol bilan solishtirish shakli: lotin, kichik harf, bitta apostrof."""
    s = to_latin(word).lower().strip()
    for ch in "‘’ʻʼ`´":
        s = s.replace(ch, "'")
    return " ".join(s.split())


@dataclass(frozen=True)
class CategoryDef:
    key: str
    name: str
    keywords: tuple[str, ...]  # normallashtirilgan
    generic: tuple[str, ...]

    @property
    def is_branch(self) -> bool:
        return self.key == BRANCH_KEY


def parse_keywords(raw: str) -> list[str]:
    """"kredit, ipoteka;  qarz" -> ["kredit", "ipoteka", "qarz"] (takrorsiz)."""
    out: list[str] = []
    for part in raw.replace(";", ",").replace("\n", ",").split(","):
        w = " ".join(part.split())
        if w and w.lower() not in {x.lower() for x in out}:
            out.append(w)
    return out


def make_def(key: str, name: str, keywords: str) -> CategoryDef:
    kws = tuple(dict.fromkeys(_norm(k) for k in parse_keywords(keywords)))
    # Kalit so'z berilmagan turkum ham savolda NOMI bilan topilsin
    if not kws and key not in _BUILTIN_GENERIC and key != "other":
        kws = (_norm(name),)
    generic = _BUILTIN_GENERIC.get(key, tuple(k.replace("'", "") for k in kws))
    return CategoryDef(key=key, name=name.strip(), keywords=kws, generic=generic)


DEFAULT_CATEGORIES: list[CategoryDef] = [make_def(*row) for row in _DEFAULTS]

_TTL_SECONDS = 60.0
_cache: tuple[float, list[CategoryDef]] | None = None


def invalidate_categories() -> None:
    """Admin turkumni o'zgartirdi — keyingi savol yangi ro'yxatni o'qiydi."""
    global _cache
    _cache = None


# Admin paneldagi "Hujjatlar (PDF)" orqali yuklangan hujjatlar shu turkumga
# tushadi (qara: documents_category_key).
DOCUMENTS_KEY = "documents"
DOCUMENTS_NAME = "Hujjatlar"


def _same_category(c_key: str, c_name: str, key: str, name: str) -> bool:
    return c_key == key or _norm(c_name) == _norm(name)


async def _create_named_category(key: str, name: str) -> str:
    """Turkumni bazada topadi, bo'lmasa yaratadi (testda almashtiriladi)."""
    repo = KbCategoryRepository()
    async with async_session() as session:
        rows = await repo.list_ordered(session)
        for c in rows:
            if _same_category(c.key, c.name, key, name):
                return c.key
        order = await repo.max_sort_order(session) + 10
        # Kalit so'zlar bo'sh — kerak bo'lsa admin panelda qo'shiladi
        await repo.create(
            session,
            {"key": key, "name": name, "keywords": "", "sort_order": order},
            commit=True,
        )
    invalidate_categories()
    return key


async def _create_documents_category() -> str:
    return await _create_named_category(DOCUMENTS_KEY, DOCUMENTS_NAME)


async def named_category_key(
    key: str, name: str, create: Callable[[], Awaitable[str]] | None = None
) -> str | None:
    """Avtomatik yuklanadigan yozuvlar turkumining kaliti ("Hujjatlar",
    "Yangiliklar", "E'lonlar"). Admin shu nomli turkum yaratgan bo'lsa —
    o'shasi, yo'q bo'lsa yangisi yaratiladi. Xato bo'lsa None: yuklash
    to'xtamasin, yozuv shunchaki turkumsiz qoladi."""
    try:
        for c in await kb_categories():
            if _same_category(c.key, c.name, key, name):
                return c.key
        if create is not None:
            return await create()
        return await _create_named_category(key, name)
    except Exception:  # noqa: BLE001
        logger.warning("%r turkumini aniqlab bo'lmadi", name, exc_info=True)
        return None


async def documents_category_key() -> str | None:
    """PDF orqali yuklangan hujjat uchun "Hujjatlar" turkumining kaliti."""
    return await named_category_key(
        DOCUMENTS_KEY, DOCUMENTS_NAME, create=_create_documents_category
    )


def _to_def(c: KbCategory) -> CategoryDef:
    return make_def(c.key, c.name, c.keywords or "")


async def _load_categories() -> list[CategoryDef]:
    """Bazadan o'qish (testlarda almashtiriladi — qara: tests/conftest.py)."""
    async with async_session() as session:
        rows = await KbCategoryRepository().list_ordered(session)
    return [_to_def(c) for c in rows]


async def kb_categories() -> list[CategoryDef]:
    """Barcha turkumlar admin belgilagan tartibda. Xato bo'lsa — standart
    ro'yxat (bot ishlashda davom etsin)."""
    global _cache
    now = time.monotonic()
    if _cache is not None and now - _cache[0] < _TTL_SECONDS:
        return _cache[1]
    try:
        cats = await _load_categories()
    except Exception:  # noqa: BLE001
        logger.exception("Turkumlar ro'yxatini o'qib bo'lmadi — standart ro'yxat")
        return DEFAULT_CATEGORIES
    _cache = (now, cats)
    return cats


def match_categories(q: str, cats: list[CategoryDef]) -> list[CategoryDef]:
    """Savolda kalit so'zi uchragan turkumlar — ENG ANIQ moslik birinchi.

    Aniqlik: eng uzun mos kalit so'z; teng bo'lsa kalit so'zi kam (torroq)
    turkum. Shunda admin "Ipoteka" turkumini yaratsa, "ipoteka" so'zi
    kreditlar ro'yxatida ham turgan bo'lsa-da, savol Ipoteka'ga tushadi."""
    qn = _norm(q)
    flat = qn.replace("'", "")
    scored: list[tuple[int, int, int, CategoryDef]] = []
    for order, cat in enumerate(cats):
        hits = [
            k for k in cat.keywords if k in qn or k.replace("'", "") in flat
        ]
        if hits:
            scored.append((-max(len(k) for k in hits), len(cat.keywords), order, cat))
    scored.sort(key=lambda s: s[:3])
    return [s[3] for s in scored]


def payload_categories(payload: dict) -> list[str]:
    """Hujjat turkumlari kalitlari. Bitta hujjat bir NECHTA turkumda bo'lishi
    mumkin ("Avtokredit" — ham Kreditlar, ham Avtokreditlar). Eski yozuvlarda
    `category` bitta satr edi — u ham o'qiladi."""
    raw = payload.get("category")
    if isinstance(raw, str):
        return [raw] if raw else []
    if isinstance(raw, (list, tuple)):
        return list(dict.fromkeys(str(x) for x in raw if x))
    return []


# ---------- Mijoz turi: jismoniy / yuridik shaxs ----------
# Admin hujjatga qo'yadi (payload `audience`). Bo'sh — belgilanmagan.
AUDIENCES = ("individual", "legal", "both")

# Model kontekstida ko'rsatiladigan izoh (AUDIENCE qatori)
AUDIENCE_PROMPT = {
    "individual": "individuals only (jismoniy shaxslar)",
    "legal": "legal entities and entrepreneurs only (yuridik shaxslar, tadbirkorlar)",
    "both": "both individuals and legal entities",
}

# Savolda mijoz turini bildiruvchi so'z o'zaklari (lotin, apostrofsiz).
# Ruscha so'zlar to_latin orqali shu ko'rinishga keladi ("юридических" ->
# "yuridicheskix", "физических" -> "fizicheskix").
_LEGAL_STEMS = ("yuridi", "korxona", "tadbirkor", "biznes", "yatt")
_INDIVIDUAL_STEMS = ("jismoniy", "fizichesk", "fizlic")
# Mijoz turi so'zi bilan birga keladigan, o'zi shart bo'lmagan so'zlar
_AUDIENCE_FILLER = ("shaxs", "lits", "lic", "subyekt")


def _flat_words(q: str) -> list[str]:
    return _norm(q).replace("'", "").replace("-", " ").split()


def question_audience(q: str) -> str | None:
    """Savol jismoniy yoki yuridik shaxslar haqidami. Ikkalasi ham (yoki
    hech biri) aytilgan bo'lsa — None (filtr qo'llanmaydi)."""
    words = _flat_words(q)
    legal = any(w.startswith(s) for w in words for s in _LEGAL_STEMS)
    individual = any(w.startswith(s) for w in words for s in _INDIVIDUAL_STEMS)
    if legal == individual:
        return None
    return "legal" if legal else "individual"


def is_audience_word(word: str) -> bool:
    """So'z faqat mijoz turini bildiradimi ("yuridik", "shaxslar") — turkum
    ichida toraytirishda mahsulot sharti hisoblanmaydi."""
    w = word.lower()
    return any(
        w.startswith(s) for s in (*_LEGAL_STEMS, *_INDIVIDUAL_STEMS, *_AUDIENCE_FILLER)
    )


def audience_fits(item_audience: str, wanted: str | None) -> bool:
    """Hujjat so'ralgan mijoz turiga mosmi. Belgilanmagan va "ikkalasi"
    hujjatlar har doim mos (ma'lumot yo'qligi sababli yashirilmaydi)."""
    if not wanted or item_audience in ("", "both"):
        return True
    return item_audience == wanted


# ---------- Turkum ro'yxati mijoz turi bo'yicha guruhlangan ----------
# "Kredit turlari" savoliga, mijoz turi aytilmagan bo'lsa, ro'yxat jismoniy va
# yuridik shaxslarga ajratib beriladi va kimga kerakligi so'raladi. Raqamlash
# guruhlar bo'ylab UZLUKSIZ — "7" deb tanlash (_resolve_list_choice) ishlaydi.
AUDIENCE_HEADINGS: dict[str, str] = {
    "individual": "Jismoniy shaxslar uchun:",
    "legal": "Yuridik shaxslar va tadbirkorlar uchun:",
    "both": "Jismoniy va yuridik shaxslar uchun:",
    "": "Mijoz turi ko'rsatilmagan:",
}
AUDIENCE_LIST_CLOSING = (
    "Qaysi biri bo'yicha batafsil ma'lumot beray? Nomini yoki tartib raqamini "
    "yozing. Faqat bitta mijoz turi kerak bo'lsa, \"jismoniy\" yoki "
    "\"yuridik\" deb yozing."
)


def audience_groups(items: list[tuple[str, str]], cyrillic: bool = False) -> str | None:
    """[(nom, mijoz_turi)] -> guruhlangan raqamli ro'yxat. Turkumda jismoniy
    HAM yuridik mahsulot bo'lmasa — None (guruhlash ma'nosiz, oddiy ro'yxat)."""
    kinds = {aud if aud in AUDIENCES else "" for _, aud in items}
    if not {"individual", "legal"} <= kinds:
        return None
    lines: list[str] = []
    n = 0
    for key in ("individual", "legal", "both", ""):
        group = [t for t, aud in items if (aud if aud in AUDIENCES else "") == key]
        if not group:
            continue
        if lines:
            lines.append("")
        head = AUDIENCE_HEADINGS[key]
        lines.append(to_cyrillic(head) if cyrillic else head)
        for title in group:
            n += 1
            lines.append(f"{n}. {title}")
    return "\n".join(lines)


# Javobda "yuridik", "jismoniy uchun", "tadbirkorlar uchunchi" kabi so'zlardan
# tashqari ruxsat etilgan so'zlar
_AUDIENCE_REPLY_EXTRA = ("uchun", "uchunchi", "kerak", "menga", "mijoz", "bu", "va", "ga")


def audience_followup(question: str, last_assistant: str | None, last_user: str | None) -> str | None:
    """Guruhlangan ro'yxatdan keyingi qisqa javob ("yuridik", "jismoniy
    shaxslar uchun") -> oldingi savol + mijoz turi ("kredit turlari yuridik").
    Shunda bot shu turkumni faqat o'sha mijoz turi bilan qayta beradi.
    Boshqa har qanday xabar — None."""
    if not last_assistant or not last_user:
        return None
    if question_audience(question) is None:
        return None
    words = _flat_words(to_latin(question))
    if not words or len(words) > 5:
        return None
    if not all(is_audience_word(w) or w in _AUDIENCE_REPLY_EXTRA for w in words):
        return None
    shown = to_latin(last_assistant)
    if AUDIENCE_HEADINGS["individual"] not in shown or AUDIENCE_HEADINGS["legal"] not in shown:
        return None
    return f"{to_latin(last_user).strip()} {question.strip()}"
