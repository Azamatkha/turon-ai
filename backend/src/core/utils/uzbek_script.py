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


# Bank/moliya sohasida tez-tez uchraydigan INGLIZCHA/BREND so'zlar — bularni
# harf-baharf kirillga o'girish ("MasterCard" -> "Мастеркард") g'alati va
# noqulay ko'rinadi, shuning uchun bunday so'zlar HAR DOIM original (lotincha)
# holicha qoldiriladi, matnning qolgan qismi kabi o'girilmaydi.
BRAND_WORDS: set[str] = {
    "visa", "mastercard", "master", "card", "humo", "uzcard", "unionpay",
    "unpay", "paypal", "swift", "iban", "atm", "pos", "pin", "cvv", "cvc",
    "sms", "id", "otp", "online", "secure", "3d",
    "gold", "classic", "standard", "standart", "business", "platinum",
    "premium", "world", "electron", "instant",
}

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'‘’.\-]*")


def _translit_word(m: re.Match[str]) -> str:
    word = m.group(0)
    bare = word.strip(".-").lower()
    if bare in BRAND_WORDS:
        return word  # inglizcha/brend so'z — o'zgarishsiz
    return _PATTERN.sub(_sub, word)


_URL_RE = re.compile(r"https?://\S+")


def to_cyrillic(text: str) -> str:
    """Lotincha o'zbek matnni kirillga o'giradi.

    Ikki narsa O'ZGARTIRILMAYDI:
    - URL manzillar (masalan "Batafsil: <url>" qatoridagi havola) — aks holda
      havola ishlamay qolardi;
    - BRAND_WORDS ro'yxatidagi inglizcha/brend so'zlar (Visa, MasterCard,
      UzCard, Gold, 3D, Secure...) — ularni harf-baharf o'girish noqulay
      ko'rinadi."""
    parts = _URL_RE.split(text)
    urls = _URL_RE.findall(text)
    out = [_WORD_RE.sub(_translit_word, parts[0])]
    for url, rest in zip(urls, parts[1:]):
        out.append(url)
        out.append(_WORD_RE.sub(_translit_word, rest))
    return "".join(out)


_CYRILLIC_RE = re.compile("[Ѐ-ӿ]")
_LATIN_RE = re.compile("[a-zA-Z]")

# Teskari yo'nalish: kirill -> lotin. Kerak, chunki BAZA va barcha ichki
# moslashtirish (mahsulot nomlari, turkum kalit so'zlari, embedding qidiruvi)
# LOTINCHA ishlaydi — foydalanuvchi kirillcha yozganda savolni shu yerda
# lotinga keltiramiz.
_CYR_TO_LAT: dict[str, str] = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh",
    "ъ": "'", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "ў": "o'", "қ": "q", "ғ": "g'", "ҳ": "h",
}

_CYR_PATTERN = re.compile("|".join(sorted(_CYR_TO_LAT, key=len, reverse=True)), re.IGNORECASE)


def _sub_lat(m: re.Match[str]) -> str:
    cyr = m.group(0)
    lat = _CYR_TO_LAT.get(cyr.lower(), cyr)
    if not lat:
        return ""
    if cyr.isupper() and len(cyr) > 1:
        return lat.upper()
    if cyr[:1].isupper():
        return lat[0].upper() + lat[1:]
    return lat


def to_latin(text: str) -> str:
    """Kirillcha o'zbek matnni lotinga o'giradi (URL'larga tegmaydi).
    Lotincha matn o'zgarishsiz qaytadi."""
    parts = _URL_RE.split(text)
    urls = _URL_RE.findall(text)
    out = [_CYR_PATTERN.sub(_sub_lat, parts[0])]
    for url, rest in zip(urls, parts[1:]):
        out.append(url)
        out.append(_CYR_PATTERN.sub(_sub_lat, rest))
    return "".join(out)


def is_cyrillic_text(text: str) -> bool:
    """Matnda lotincha harflarga qaraganda kirillcha harflar ko'proq (yoki
    faqat kirill bor)mi — foydalanuvchi qaysi alifboda yozganini aniqlash
    uchun."""
    cyr = len(_CYRILLIC_RE.findall(text))
    lat = len(_LATIN_RE.findall(text))
    return cyr > 0 and cyr >= lat


class StreamingTransliterator:
    """Oqim (streaming) bo'laklarini kirillga XAVFSIZ o'giradi.

    Harf-baharf emas, SO'Z CHEGARASI bo'yicha buferlaydi: bo'lak oxiridagi
    hali tugamagan so'z (bo'shliqqача yetib kelmagan) navbatdagi bo'lak
    kelguncha ushlab turiladi, keyin to'liq so'z bir yo'la `to_cyrillic`ga
    beriladi. Bu digraflarning ("sh", "ch", "o'"...), URL manzillarning va
    BRAND_WORDS so'zlarining (masalan "MasterCard") ikki bo'lak orasida
    bo'linib, noto'g'ri o'girilib qolishining oldini butunlay oladi —
    chunki ular hech qachon TO'LIQ bo'lmagan holda `to_cyrillic`ga
    yuborilmaydi."""

    def __init__(self) -> None:
        self._pending = ""

    def feed(self, delta: str) -> str:
        buf = self._pending + delta
        m = re.search(r"\S+\Z", buf)
        if m is None:
            complete, self._pending = buf, ""
        else:
            complete, self._pending = buf[: m.start()], buf[m.start() :]
        return to_cyrillic(complete) if complete else ""

    def flush(self) -> str:
        rest, self._pending = self._pending, ""
        return to_cyrillic(rest) if rest else ""
