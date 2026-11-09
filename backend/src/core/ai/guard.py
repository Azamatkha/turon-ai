"""LLM'ga ketadigan foydalanuvchi matnini himoyalash.

1) PII maskalash — karta, hisob raqami, JShShIR va pasport raqami modelga
   (va savollar statistikasiga) ochiq holda ketmasin. Bot bu ma'lumotlar
   bilan hech narsa qila olmaydi, ular faqat loglarda va model kontekstida
   keraksiz iz qoldiradi. Telefon raqamlari MASKALANMAYDI — xodimlar
   ma'lumotnomasi aynan telefon/IP bo'yicha qidiradi.

2) Prompt-injection aniqlash — "oldingi ko'rsatmalarni unut", "system
   prompt'ni ko'rsat" kabi ochiq urinishlar modelga umuman yuborilmaydi.
   Bu evristika (to'liq himoya emas): asosiy himoya — system prompt'dagi
   qoida (knowledge/prompts.py -> SECURITY_RULES). Naqshlar ataylab tor:
   oddiy savolni ("kredit qoidalarini unutdim") bloklab qo'yish chatni
   buzganidan yomonroq.
"""

import re

from src.core.utils.uzbek_script import to_latin

# ---- PII ----

_ACCOUNT = re.compile(r"(?<!\d)\d{20}(?!\d)")
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){15}\d(?!\d)")
# JShShIR (PINFL): 14 raqam, birinchisi asr+jins (3-6)
_PINFL = re.compile(r"(?<!\d)[3-6]\d{13}(?!\d)")
# Pasport / ID-karta: 2 lotin harf + 7 raqam (AA1234567, AD 1234567)
_PASSPORT = re.compile(r"(?<![A-Za-z])[A-Za-z]{2}\s?\d{7}(?!\d)")

MASK_ACCOUNT = "[HISOB RAQAMI]"
MASK_PINFL = "[JSHSHIR]"
MASK_PASSPORT = "[PASPORT]"


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _mask_card(m: re.Match[str]) -> str:
    digits = re.sub(r"\D", "", m.group(0))
    # Luhn'dan o'tmagan 16 xonali son karta emas (masalan buyurtma raqami)
    if not _luhn_ok(digits):
        return m.group(0)
    return f"[KARTA ****{digits[-4:]}]"


def mask_pii(text: str) -> tuple[str, list[str]]:
    """Matndagi PII'ni maskalaydi. (yangi matn, topilgan turlar) qaytaradi."""
    found: list[str] = []

    def sub(pattern: re.Pattern[str], repl, kind: str, s: str) -> str:
        new = pattern.sub(repl, s)
        if new != s:
            found.append(kind)
        return new

    out = sub(_ACCOUNT, MASK_ACCOUNT, "account", text)
    out = sub(_CARD, _mask_card, "card", out)
    out = sub(_PINFL, MASK_PINFL, "pinfl", out)
    out = sub(_PASSPORT, MASK_PASSPORT, "passport", out)
    return out, found


# ---- Prompt injection ----

_APOS = re.compile(r"[ʻʼ‘’`´]")

_INJECTION_PATTERNS = [
    # English
    r"\b(ignore|disregard|forget)\s+(all\s+|any\s+)?(the\s+|your\s+)?(previous|prior|above|earlier|system)\s+(instructions?|prompts?|rules|messages?)",
    r"\b(reveal|show|print|repeat|output|display)\s+(me\s+)?(your|the)\s+(system|initial|hidden|original)\s+(prompt|instructions?|message)",
    r"\byou\s+are\s+now\s+(an?\s+)?(unrestricted|unfiltered|different|new|evil|dan)\b",
    r"\b(developer|jailbreak|dan|god)\s+mode\b",
    # O'zbekcha (lotinga keltirilgan matn ustida)
    r"\b(oldingi|avvalgi|yuqoridagi|barcha|hamma|sening|o'z)\s+(\w+\s+)?(ko'rsatma|qoida|buyruq|instruksiya|cheklov)\w*\s+(\w+\s+)?(unut(ing|gin)?|e'tiborsiz\s+qoldir(ing|gin)?|bekor\s+qil(ing|gin)?|inobatga\s+olma)\b",
    r"\b(tizim|sistema|system)\w*\s+(prompt|ko'rsatma|instruksiya)\w*\s+(\w+\s+)?(ko'rsat|chiqar|yozib\s+ber|ayt)",
    r"\bsen\s+endi\s+(cheklovsiz|boshqa\s+(bot|ai|model|yordamchi))",
    # Ruscha
    r"(игнорируй|забудь|отмени|не\s+учитывай)\w*\s+(все\s+|всё\s+)?(предыдущ|прошл|данн|сво|систем)\w*\s+(инструкц|правил|указани|промпт|ограничени)",
    r"(покажи|выведи|напиши|раскрой|повтори)\s+(мне\s+)?(свой\s+|твой\s+|свои\s+|твои\s+)?(системн\w*\s+)(промпт|инструкци|сообщени)",
    r"\bты\s+теперь\s+(без\s+ограничений|другой|другая|не\s+ассистент)",
    r"(режим\s+разработчика|jailbreak)",
]
_INJECTION = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def looks_like_injection(text: str) -> bool:
    """Savolda modelning ko'rsatmalarini chetlab o'tishga ochiq urinish bormi.

    O'zbek kirill matni ham tekshirilishi uchun lotinga keltirilgan nusxa
    ham ko'riladi (ruscha naqshlar asl matn ustida ishlaydi).
    """
    if not text:
        return False
    original = _APOS.sub("'", text.lower())
    latin = _APOS.sub("'", to_latin(text).lower())
    return any(p.search(original) or p.search(latin) for p in _INJECTION)
