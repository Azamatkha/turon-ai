"""Javob tilini aniqlash: o'zbek lotin / o'zbek kirill / rus.

Ilgari til faqat ALIFBO bo'yicha aniqlanardi: kirill harfli har qanday savol
"o'zbek kirill" deb hisoblanardi. Natijada ruscha savolga model o'zbekcha
(lotin) javob yozar, keyin u harf-baharf kirillga o'girilib, rus tilida
so'ragan odam o'zbekcha kirill matnni olardi. Endi kirill matnda o'zbek va
rus belgilarini sanab, qaysi til ekanini ajratamiz.
"""

import re
from typing import Literal

from src.core.utils.uzbek_script import is_cyrillic_text
from src.knowledge.schemas import ChatTurn

ReplyLang = Literal["uz", "uz_cyrl", "ru"]

# Faqat o'zbek kirillida bor harflar — bittasi ham yetarli dalil
_UZ_CYRL_LETTERS = set("ўқғҳЎҚҒҲ")
# O'zbek kirillida deyarli uchramaydigan rus harflari
_RU_LETTERS = set("ыщЫЩ")

# Ko'p uchraydigan so'zlar. Maxsus harfsiz yozilgan o'zbekcha ("нима керак",
# "учун") va ruscha ("какой процент") savolni shular ajratadi.
_RU_WORDS = {
    "что", "как", "какой", "какая", "какие", "каких", "где", "когда",
    "сколько", "почему", "зачем", "это", "мне", "меня", "можно", "нужно",
    "есть", "для", "или", "если", "при", "по", "на", "не", "я", "вы", "вас",
    "у", "в", "и", "с", "от", "до", "пожалуйста", "скажите", "расскажите",
    "подскажите", "условия", "процент", "проценты", "ставка", "курс",
    "карта", "карты", "карту", "вклад", "вклады", "номер", "телефон",
    "сотрудник", "сотрудника", "отдел", "филиал", "здравствуйте", "привет",
    "спасибо", "значит", "слово", "слова", "перевод", "переведи",
}
_UZ_WORDS = {
    "нима", "қанча", "канча", "қандай", "кандай", "учун", "керак",
    "бор", "йўқ", "йук", "ва", "билан", "бўйича", "буйича", "қаерда",
    "каерда", "ким", "мен", "сиз", "эмас", "ҳақида", "хакида", "беринг",
    "айтинг", "олиш", "қилиш", "килиш", "рахмат", "раҳмат", "ассалому",
    "алайкум", "салом", "маъноси", "сўзи", "сузи", "ёрдам", "қайси", "кайси",
}

_WORD_RE = re.compile(r"[А-Яа-яЁёЎўҚқҒғҲҳ]+")


def _text_lang(text: str) -> ReplyLang:
    """Bitta matnning tili (harf bo'lishi shart)."""
    if not is_cyrillic_text(text):
        return "uz"
    if any(c in _UZ_CYRL_LETTERS for c in text):
        return "uz_cyrl"
    words = [w.lower() for w in _WORD_RE.findall(text)]
    ru = sum(1 for w in words if w in _RU_WORDS)
    uz = sum(1 for w in words if w in _UZ_WORDS)
    if any(c in _RU_LETTERS for c in text):
        ru += 2
    # Teng bo'lsa — o'zbek kirill: bank asosan o'zbek tilida ishlaydi va
    # eski xatti-harakat (kirill -> o'zbek kirill) saqlanadi.
    return "ru" if ru > uz else "uz_cyrl"


def detect_reply_lang(question: str, history: list[ChatTurn] | None) -> ReplyLang:
    """Javob qaysi tilda yozilishi kerak.

    Savolda harf bo'lmasa (ro'yxatdan "3" deb tanlash) — tilni suhbatdagi
    oxirgi matnli foydalanuvchi xabaridan meros qilib olamiz, aks holda
    tanlovdan keyin javob boshqa tilga "sakrab" ketardi."""
    if any(c.isalpha() for c in question):
        return _text_lang(question)
    for turn in reversed(history or []):
        if turn.role == "user" and any(c.isalpha() for c in turn.content):
            return _text_lang(turn.content)
    return "uz"
