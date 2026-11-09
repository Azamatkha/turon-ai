"""So'kinish va haqoratni aniqlash (lug'at qatlami — model chaqirilmaydi).

Xavfli/noqonuniy so'rovlarni (giyohvand modda, qurol, pul yuvish...) bu
modul ANIQLAMAYDI: ular ko'pincha yashirin yoziladi ("4 kg unga o'xshash
narsa, narxi 80 mln") va so'z ro'yxati bilan ushlanmaydi — ularni savol
MA'NOSINI tushunadigan router modeli aniqlaydi (knowledge/router.py ->
Intent.HARMFUL). Bu yerda faqat so'kinish: u aniq so'zlar bilan yoziladi.

Noto'g'ri bloklash (false positive) foydalanuvchini so'kingan deb adminga
yuborardi — shuning uchun FAQAT butun so'z yoki so'z boshi (o'zak) bo'yicha
tekshiriladi: "хлеб" ichidagi "еб", "harom" (halol/harom) kabi so'zlar
tegilmaydi.
"""

import re

from src.core.utils.uzbek_script import to_latin

# Harflarni raqam/belgi bilan yashirish: "s0k1n" -> "sokin"
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "@": "a", "$": "s", "ё": "е"})
_WORD = re.compile(r"[a-zа-яўқғҳ']+")
# Uzaytirib yozish: "suuuuka" -> "suka" (faqat moslashtirish uchun)
_REPEAT = re.compile(r"(.)\1+")

# So'z shu bilan BOSHLANSA — so'kinish (qo'shimchalar bilan: "jalablar", "сукам")
_PREFIXES = (
    # o'zbekcha (lotinga keltirilgan matn)
    "jalab", "qanjiq", "onangni", "onangn", "sikay", "sikam", "sikib", "sikish",
    "sikdim", "siktir", "dalbayob", "dalbayop", "gandon", "pidaras", "pidor",
    "xuyna", "naxuy", "nahuy", "blyat", "blyad",
    # ruscha
    "хуй", "хуе", "хуя", "хуё", "пизд", "ебан", "ебат", "ебал", "еблан", "заеб",
    "выеб", "наеб", "отъеб", "уеб", "долбоеб", "мудак", "мудил", "пидор", "пидар",
    "гандон", "шлюх", "бляд", "блят", "сучар", "нахуй", "похуй",
    # inglizcha
    "fuck", "motherf", "bitch", "asshole", "cunt",
)
# Faqat AYNAN shu so'z bo'lsa (boshqa so'zning boshi bo'lishi mumkin)
_EXACT = frozenset({"suka", "suki", "сука", "суки", "бля", "xuy", "blya", "shit", "ske"})


def _variants(text: str) -> set[str]:
    """Matndagi so'zlar: asl (kirill) va lotinlashgan, belgi-almashtirishsiz va
    takroriy harflarsiz ko'rinishlarda."""
    low = text.lower().translate(_LEET)
    words: set[str] = set()
    for source in (low, to_latin(low)):
        for w in _WORD.findall(source):
            w = w.strip("'")
            if not w:
                continue
            words.add(w)
            words.add(_REPEAT.sub(r"\1", w))
    return words


def find_profanity(text: str) -> list[str]:
    """Topilgan so'kinish so'zlari (bo'sh ro'yxat — toza matn)."""
    if not text:
        return []
    found = []
    for w in _variants(text):
        if w in _EXACT or any(w.startswith(p) for p in _PREFIXES):
            found.append(w)
    return sorted(set(found))


def has_profanity(text: str) -> bool:
    return bool(find_profanity(text))
