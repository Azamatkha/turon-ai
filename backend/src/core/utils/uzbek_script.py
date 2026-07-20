"""O'zbek lotin -> kirill transliteratsiyasi.

Bu TARJIMA emas — bir xil so'zlarni boshqa alifboda yozish (harf almashtirish).
AI javoblari system prompt talabiga ko'ra doim LOTINCHA yoziladi (bitta manba —
bazani ikki alifboda saqlash shart emas); foydalanuvchi savolni KIRILLCHA
yozgan bo'lsa, javobni shu yerda kirillga o'giramiz.

Eslatma: soddalashtirish sifatida so'z boshidagi "e" har doim "е" ga o'giriladi
("э" bo'lishi kerak bo'lgan holatlar — masalan "el", "endi" — ham "е" bo'lib
qoladi). Bank mahsulot nomlari/atamalari uchun bu deyarli sezilmaydi.
"""

import re

_DIGRAPHS: list[tuple[str, str]] = [
    ("sh", "ш"),
    ("ch", "ч"),
    ("yo", "ё"),
    ("yu", "ю"),
    ("ya", "я"),
    ("ng", "нг"),
]

_SINGLE: dict[str, str] = {
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "ҳ",
    "i": "и", "j": "ж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о",
    "p": "п", "q": "қ", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в",
    "x": "х", "y": "й", "z": "з",
}

# Turli klaviatura/matn manbalarida uchraydigan apostrof belgilari — hammasi
# bitta xil deb hisoblanadi ("o'", "o‘", "o’" — barchasi "ў").
_APOSTROPHES = "'‘’ʻʼ`"

_MAP: dict[str, str] = {"o'": "ў", "g'": "ғ", **dict(_DIGRAPHS), **_SINGLE}

_apos_cls = "[" + re.escape(_APOSTROPHES) + "]"
_PATTERN = re.compile(
    "o" + _apos_cls + "|" + "g" + _apos_cls + "|"
    "sh|ch|yo|yu|ya|ng|[a-z]|" + _apos_cls,
    re.IGNORECASE,
)

# Ikki harfli birikmaning BIRINCHI harfi bo'lishi mumkin bo'lgan belgilar —
# oqim (streaming) rejimida bo'lak chegarasida ushlab turish uchun ishlatiladi.
_DIGRAPH_STARTERS = set("scyong")


def _apply_case(cyr: str, latin: str) -> str:
    if latin.isupper() and len(latin) > 1:
        return cyr.upper()
    if latin[:1].isupper():
        return cyr[0].upper() + cyr[1:]
    return cyr


def _sub(m: re.Match[str]) -> str:
    latin = m.group(0)
    if len(latin) == 1 and latin in _APOSTROPHES:
        return "ъ"
    key = latin.lower()
    if len(key) == 2 and key[1] in _APOSTROPHES:
        key = key[0] + "'"
    cyr = _MAP.get(key)
    return _apply_case(cyr, latin) if cyr else latin


def to_cyrillic(text: str) -> str:
    """Lotincha o'zbek matnni kirillga o'giradi."""
    return _PATTERN.sub(_sub, text)


_CYRILLIC_RE = re.compile("[Ѐ-ӿ]")
_LATIN_RE = re.compile("[a-zA-Z]")


def is_cyrillic_text(text: str) -> bool:
    """Matnda lotincha harflarga qaraganda kirillcha harflar ko'proq (yoki
    faqat kirill bor)mi — foydalanuvchi qaysi alifboda yozganini aniqlash
    uchun."""
    cyr = len(_CYRILLIC_RE.findall(text))
    lat = len(_LATIN_RE.findall(text))
    return cyr > 0 and cyr >= lat


class StreamingTransliterator:
    """Oqim (streaming) bo'laklarini kirillga XAVFSIZ o'giradi — ikki harfli
    birikmalar (sh, ch, yo, yu, ya, ng, o', g') ikki bo'lak orasida bo'linib
    qolsa noto'g'ri o'girilib qolmasligi uchun, bo'lak oxiridagi "boshlovchi"
    belgini keyingi bo'lak kelguncha ushlab turadi."""

    def __init__(self) -> None:
        self._pending = ""

    def feed(self, delta: str) -> str:
        buf = self._pending + delta
        if buf and buf[-1].lower() in _DIGRAPH_STARTERS:
            safe, self._pending = buf[:-1], buf[-1]
        else:
            safe, self._pending = buf, ""
        return to_cyrillic(safe)

    def flush(self) -> str:
        rest, self._pending = self._pending, ""
        return to_cyrillic(rest)
