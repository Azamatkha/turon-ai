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


_URL_RE = re.compile(r"https?://\S+")


def to_cyrillic(text: str) -> str:
    """Lotincha o'zbek matnni kirillga o'giradi. URL manzillar (masalan
    "Batafsil: <url>" qatoridagi havola) O'ZGARTIRILMAYDI — aks holda havola
    ishlamay qolardi."""
    parts = _URL_RE.split(text)
    urls = _URL_RE.findall(text)
    out = [_PATTERN.sub(_sub, parts[0])]
    for url, rest in zip(urls, parts[1:]):
        out.append(url)
        out.append(_PATTERN.sub(_sub, rest))
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


# "http"/"https" so'zi qurilayotganda bo'lak chegarasida chala transliteratsiya
# qilib qo'ymaslik uchun — buferning oxiri shu prefikslardan biriga
# BOSHLANISHI mumkin bo'lsa, to'liq URL yoki uning yo'qligi aniq bo'lguncha
# kutamiz.
_URL_START_PREFIXES = ["https://", "http://"]


def _url_start_hold_len(buf: str) -> int:
    """Buferning oxiri "http"/"https://" prefiksining BOSHLANG'ICH qismiga mos
    kelsa (masalan "...matn htt") va bu SO'Z BOSHIDA bo'lsa (harfdan keyin
    emas — aks holda "sh", "boshqa" kabi so'zlar oxiri ham noto'g'ri "URL
    boshlanishi" deb ushlab qolinardi), shu qismni ushlab turish uchun
    uzunlikni qaytaradi. Aks holda 0."""
    low = buf.lower()
    max_len = max(len(p) for p in _URL_START_PREFIXES)
    for n in range(min(len(buf), max_len), 0, -1):
        start = len(buf) - n
        if start > 0 and buf[start - 1].isalnum():
            continue  # so'z ichida — URL boshlanishi emas
        tail = low[start:]
        if any(p.startswith(tail) for p in _URL_START_PREFIXES):
            return n
    return 0


class StreamingTransliterator:
    """Oqim (streaming) bo'laklarini kirillga XAVFSIZ o'giradi:
    - ikki harfli birikmalar (sh, ch, yo, yu, ya, ng, o', g') ikki bo'lak
      orasida bo'linib qolsa noto'g'ri o'girilib qolmasligi uchun, bo'lak
      oxiridagi "boshlovchi" belgini keyingi bo'lak kelguncha ushlab turadi;
    - URL manzil ("https://...") boshlanayotganini sezsa, butun URL tugab
      (bo'sh joy/qator oxiri kelguncha) hech narsani o'girmaydi — aks holda
      havola harf-baharf (noto'g'ri) o'girilib qolardi."""

    def __init__(self) -> None:
        self._pending = ""
        self._in_url = False

    def feed(self, delta: str) -> str:
        buf = self._pending + delta
        out: list[str] = []

        if self._in_url:
            m = re.search(r"\s", buf)
            if m is None:
                self._pending = buf
                return ""
            out.append(buf[: m.end()])  # URL + undan keyingi bo'shliq — o'zgarmaydi
            buf = buf[m.end() :]
            self._in_url = False

        url_m = _URL_RE.search(buf)
        if url_m:
            out.append(to_cyrillic(buf[: url_m.start()]))
            if url_m.end() == len(buf):
                # URL hali tugamagan bo'lishi mumkin (keyingi bo'lakda davom etadi)
                out.append(buf[url_m.start() :])
                self._pending = ""
                self._in_url = True
                return "".join(out)
            out.append(buf[url_m.start() : url_m.end()])
            buf = buf[url_m.end() :]
            self._pending = ""
        # qolgan qismda URL yo'q — oddiy (digraf va "http" boshlanishi xavfsizligi bilan)
        hold = max(
            1 if buf and buf[-1].lower() in _DIGRAPH_STARTERS else 0,
            _url_start_hold_len(buf),
        )
        if hold:
            safe, self._pending = buf[:-hold], buf[-hold:]
        else:
            safe, self._pending = buf, ""
        out.append(to_cyrillic(safe))
        return "".join(out)

    def flush(self) -> str:
        rest, self._pending = self._pending, ""
        if self._in_url or rest.lower().startswith(("http://", "https://")):
            self._in_url = False
            return rest
        return to_cyrillic(rest)
