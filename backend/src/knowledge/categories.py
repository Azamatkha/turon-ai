"""Bilim bazasi turkumlari — bot uchun (katalog va keng savollar).

Turkumlarni ADMIN boshqaradi (kb_categories jadvali). Avtomatik taxmin yo'q:
hujjat qaysi turkumda ekanini faqat payload'dagi `category` kaliti aytadi.

Bot har savolda turkumlarga qaraydi, shuning uchun ro'yxat qisqa muddat
xotirada saqlanadi; admin o'zgartirganda kesh darhol tozalanadi.
"""

from dataclasses import dataclass
import time

from loggers import get_logger
from src.core.database.session import async_session
from src.core.utils.uzbek_script import to_latin
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
