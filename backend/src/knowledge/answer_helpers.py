"""Javob oqimining SOF yordamchi funksiyalari (xodim moslash, matn
normallashtirish, aniqlashtiruvchi savol, kurs hisobi va h.k.).

`usecases.py` dan ko'chirilgan — mantiq o'zgarmagan, faqat joyi.
"""

from datetime import timedelta
from itertools import chain, zip_longest
import re
from typing import Any

from loggers import get_logger
from src.core.ai.guard import looks_like_injection, mask_pii
from src.core.utils.datetime_utils import get_utc_now
from src.core.utils.uzbek_script import (
    to_cyrillic,
    to_latin,
)
from src.knowledge import web_search
from src.knowledge.lang import ReplyLang, is_russian_text
from src.knowledge.prompts import (
    CAPABILITIES_REPLY,
    LANGUAGE_SYSTEM,
    RU_CANNED_REPLIES,
    RU_LANGUAGE_OVERRIDE,
    RU_REPLY_OVERRIDE,
    SECURITY_RULES,
    SMALLTALK_FALLBACK_REPLY,
    WEB_LOOKUP_TOKEN,
    WEB_NOT_FOUND_TOKEN,
)
from src.knowledge.rates_scraper import RATES_URL
from src.knowledge.router import Intent, Route
from src.knowledge.schemas import (
    ChatTurn,
    SourceRef,
)
from src.main.config import config

logger = get_logger(__name__)

# ------- Xodim (telefon/IP ma'lumotnoma) qidiruv yordamchilari ------- #
# Xodimlar ma'lumoti STRUKTURAVIY — IP/telefon/ism bo'yicha ANIQ moslash embedding
# semantik qidiruvidan ishonchliroq (raqamlar semantik qidiruvda yomon topiladi).

_NAME_STOP = {"ogli", "ugli", "qizi", "kizi"}
_DEPT_STOP = {
    "departamenti", "departament", "departmenti", "dep", "bolim", "bolimi",
    "boshqarish", "boshqarmasi", "xodimlar", "xodimlarni", "xodim", "va", "ip",
    "raqam", "raqami", "raqamlari", "telefon", "markazi", "xizmatlari", "xizmat",
    "nazorat", "hisobini", "yuritish", "bosh", "menejer", "direktori",
    # "bank" hamma bo'lim nomida uchraydi — hech narsani ajratmaydi.
    "bank", "banki", "turonbank",
}

# Bo'lim nomida deyarli har doim uchraydigan, hech narsani AJRATMAYDIGAN
# so'zlar — PREFIKS bo'yicha tekshiriladi. Sabab: bazada imlo turlicha
# yozilgan ("departament", "departamenti", "departmenti" va hatto qisqargan
# "departamen"). Ro'yxatga aynan tenglik bilan tayansak, bitta harf farq
# qilgani uchun "departamen" ajratuvchi so'z deb qabul qilinib, "IT
# departament ichki raqamlari" so'roviga "Moliyaviy hisobotlar departamen"
# javob berardi (uzunroq so'z ballda "it" dan ustun kelardi).
_DEPT_STOP_PREFIXES = (
    "departam", "departm", "boshqarm", "bolim", "xizmat", "markaz",
)


def _is_dept_stopword(token: str) -> bool:
    return token in _DEPT_STOP or any(
        token.startswith(p) for p in _DEPT_STOP_PREFIXES
    )


def _dept_token_hit(token: str, qwords: set[str]) -> bool:
    """Bo'lim so'zi savolda bormi — SO'Z sifatida, matn ichidagi bo'lak emas.

    Ilgari `token in q_lower` ishlatilardi: "departamen" savoldagi
    "departament" so'zining ICHIGA tushib, moslik deb hisoblanardi."""
    if token in qwords:
        return True
    # Qo'shimchali shakl ("moliyaviy" ~ "moliyaviyning") — kamida 5 belgi.
    return any(
        min(len(token), len(w)) >= 5
        and (w.startswith(token) or token.startswith(w))
        for w in qwords
    )


# Savoldagi ism deb hisoblanmaydigan umumiy so'zlar (aks holda "raqami" kabi
# so'z tasodifan biror ismning boshiga mos kelib qolardi)
_QUERY_STOP = {
    "ip", "raqam", "raqami", "raqamlari", "raqamini", "nomer", "ichki",
    "xodim", "xodimi", "xodimlar", "xodimlari", "xodimning", "hodim",
    "telefon", "telefoni", "kim", "kimniki", "kimning", "qaysi", "qanday",
    "nima", "necha", "bering", "ber", "beray", "top", "toping", "kerak",
    "departament", "departamenti", "bolim", "bolimi", "bolimning",
    "boshqarma", "boshqarmasi", "lavozim", "lavozimi", "haqida", "bilan",
    # Kundalik olmosh/yordamchi so'zlar — bularsiz "men" so'zi "MENGLIYEV"
    # familiyasining boshiga mos kelib, filial savolini xodim qidiruviga
    # tortib ketardi.
    "men", "menga", "meni", "mening", "sen", "senga", "siz", "sizga",
    "sizning", "biz", "bizga", "bizning", "ular", "ularga", "shu", "shuni",
    "bor", "bormi", "yoq", "hozir", "hozirda", "yaqin", "eng", "ham",
    "uchun", "lekin", "ammo", "yana", "faqat", "kabi", "yoki", "agar",
    "iltimos", "salom", "rahmat", "mumkin", "boladi", "qilib", "deb",
}


# Savol XODIMLAR haqida EMAS, balki bank mahsuloti/filiali haqida ekanini
# bildiruvchi so'zlar. Bunday so'z bo'lsa (va aniq xodim-niyat bo'lmasa),
# xodim qidiruvi umuman ishga tushmaydi — aks holda oddiy so'zlar tasodifan
# xodim ismiga mos kelib, mutlaqo boshqa javob qaytarardi.
_NON_EMPLOYEE_SIGNALS = (
    "filial", "bxm", "bank xizmatlari", "manzil", "kocha", "tuman",
    "viloyat", "shahar", "yaqin", "joylash", "kredit", "karta", "omonat",
    "depozit", "ipoteka", "mikroqarz", "qarz", "valyuta", "kurs",
    "otkazma", "foiz", "stavka", "ish tartibi", "ish vaqti",
)


def _has_non_employee_signal(q_lower: str) -> bool:
    """Savolda mahsulot/filial mavzusiga oid aniq belgi bormi."""
    return any(s in q_lower for s in _NON_EMPLOYEE_SIGNALS)


def _words(s: str) -> list[str]:
    return re.findall(r"[0-9a-zа-яёўқғҳ]+", s.lower())


# Ism solishtirishda apostrof so'zni BO'LMASLIGI kerak. Aks holda
# "o'zbekiston" -> "zbekiston", "Navro'zbek" -> "navro" + "zbek" bo'lib,
# "zbek" prefiksi tasodifan mos kelardi va "O'zbekiston Respublikasi
# Konstitutsiyasi" savoliga xodim kontakti qaytarilardi.
_NAME_APOS_RE = re.compile("['‘’ʻʼ`´]")


def _drop_apos(s: str) -> str:
    return _NAME_APOS_RE.sub("", s)


def _name_norm(token: str) -> str:
    """Ism-familiyani solishtirish uchun normallashtiradi. O'zbek ismlari
    transliteratsiyasida X va H ko'pincha almashtiriladi ("Xamdamboyev" /
    "Hamdamboyev"), apostrof turlicha yoziladi — shularni bir xillashtiramiz."""
    t = token.lower()
    t = re.sub(r"['ʻʼ`’]", "", t)
    t = t.replace("x", "h")
    return t


def _is_ogli_marker(word: str) -> bool:
    """So'z "o'g'li"/"qizi"/"ugli" (otasining ismi belgisi)mi — apostrof va
    registrdan qat'i nazar."""
    w = re.sub(r"[^a-zа-яёў]", "", word.lower())
    return w in ("ogli", "ugli", "qizi", "ўғли", "қизи")


def _own_name_tokens(fish: str) -> list[str]:
    """F.I.SH'dan FAQAT shaxsning o'z ismi/familiyasini qaytaradi — otasining
    ismini (otchestvo) tashlab yuboradi. Aks holda "Ixtiyor ip raqami" so'rovi
    "Isroilov Isroil IXTIYOR o'g'li" kabi otasining ismi mos kelgan begona
    xodimni ham qaytarardi. Otchestvo belgilari:
      * "o'g'li"/"qizi" dan OLDINGI so'z (otasining ismi);
      * "-ovich/-evich/-ovna/-evna" bilan tugagan so'z (ruscha otchestvo)."""
    raw = fish.split()
    drop: set[int] = set()
    for i, w in enumerate(raw):
        if _is_ogli_marker(w):
            drop.add(i)
            if i - 1 >= 0:
                drop.add(i - 1)  # o'g'li/qizi dan oldingi so'z = otasining ismi
    kept: list[str] = []
    for i, w in enumerate(raw):
        if i in drop:
            continue
        if w.lower().endswith(("ovich", "evich", "ovna", "evna")):
            continue
        kept.append(w)
    return [
        t
        for t in _words(_drop_apos(" ".join(kept)))
        if len(t) >= 3 and t not in _NAME_STOP
    ]


# Egalik/kelishik qo'shimchalari — "Azamatning ip raqami" so'rovida so'z
# "azamatning" bo'lib qoladi va "Azamat" bilan moslik ballini pasaytiradi
# (ba'zi ismlar umuman tushib qolardi). Uzunroq qo'shimcha avval tekshiriladi.
_UZ_SUFFIXES = ("ningki", "ining", "ning", "dagi", "ndan", "niki", "dan", "ni", "ga", "da")


def _strip_uz_suffix(token: str) -> str:
    """"Azamatning" -> "Azamat". O'zak kamida 4 harf qolsa qirqamiz — aks
    holda qisqa familiyalar ("Husni") buzilib ketardi."""
    for suf in _UZ_SUFFIXES:
        if token.endswith(suf) and len(token) - len(suf) >= 4:
            return token[: -len(suf)]
    return token


def _common_prefix_len(a: str, b: str) -> int:
    n = 0
    for ca, cb in zip(a, b):
        if ca != cb:
            break
        n += 1
    return n


# --- Xodimni MATNDAN ajratib olish -------------------------------------- #
# Xodimlar bazaga strukturaviy maydonlar (doc_type/ip/fish) bilan yozilmagan
# bo'lishi mumkin — o'shanda faqat chunk_text qoladi:
#   "Bo'lim: IT DEPARTAMENT. Lavozim: Bosh mutaxassis. F.I.SH: ... .
#    Ichki raqam (IP): 2206. Telefon: ..."
# Bu holda IP/ism/bo'lim bo'yicha qidiruv butunlay ishlamay qolardi. Matn
# formati qat'iy bo'lgani uchun uni qayta ajratib olish ishonchli.

_EMP_FIELD_RE = re.compile(
    r"(bo.?linma|bo.?lim|lavozim|f\s*\.?\s*i\s*\.?\s*sh"
    r"|ichki\s*raqam(?:\s*\(\s*ip\s*\))?|telefon)\s*:\s*",
    re.IGNORECASE,
)
# Har bir yozuv "Bo'lim:" bilan boshlanadi.
_EMP_SPLIT_RE = re.compile(r"(?=bo.?lim\s*:)", re.IGNORECASE)


def _emp_field_key(label: str) -> str | None:
    key = re.sub(r"[^a-z]", "", label.lower())
    if key.startswith("bolinma"):
        return "division"
    if key.startswith("bolim"):
        return "department"
    if key.startswith("lavozim"):
        return "position"
    if key.startswith("fish"):
        return "fish"
    if key.startswith("ichkiraqam"):
        return "ip"
    if key.startswith("telefon"):
        return "phone"
    return None


def _parse_employee_text(text: str) -> list[dict[str, Any]]:
    """Matndan xodim yozuvlarini ajratadi. Format buzilgan bo'lsa — bo'sh."""
    if ":" not in text:
        return []
    out: list[dict[str, Any]] = []
    for seg in _EMP_SPLIT_RE.split(text):
        marks = list(_EMP_FIELD_RE.finditer(seg))
        if not marks:
            continue
        rec: dict[str, Any] = {
            "department": "", "division": "", "position": "",
            "fish": "", "ip": "", "phone": "",
        }
        for i, m in enumerate(marks):
            key = _emp_field_key(m.group(1))
            if key is None:
                continue
            end = marks[i + 1].start() if i + 1 < len(marks) else len(seg)
            # Bo'shliqlarni normallashtiramiz: manbadagi qator uzilishlari
            # javobda lavozim matnini ikkiga bo'lib tashlardi ("Hisobotlarni
            # tartibga solish va\n\nMSFO boshqarmasi").
            rec[key] = " ".join(seg[m.end() : end].split()).strip(".").strip()
        # F.I.SH bo'lmasa bu xodim yozuvi emas (masalan oddiy hujjat matni).
        if rec["fish"]:
            rec["chunk_text"] = seg.strip()
            rec["doc_type"] = "employee"
            out.append(rec)
    return out


def _employees_from_payloads(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Barcha payload matnlaridan xodimlarni yig'adi (takrorlanmasdan)."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for p in payloads:
        for rec in _parse_employee_text(str(p.get("chunk_text", ""))):
            key = f"{rec['fish']}|{rec['ip']}"
            if key not in seen:
                seen.add(key)
                out.append(rec)
    return out


def _format_employee_line(e: dict[str, Any], with_dept: bool = True) -> str:
    """Bitta xodim — bir qator: F.I.SH, bo'lim, bo'linma, lavozim, IP, telefon."""
    parts: list[str] = [str(e.get("fish", "")).strip()]
    if with_dept:
        parts.append(str(e.get("department", "")).strip())
    parts.append(str(e.get("division", "")).strip())
    parts.append(str(e.get("position", "")).strip())
    ip = str(e.get("ip", "")).strip()
    parts.append(f"ichki raqam (IP): {ip}" if ip else "ichki raqam (IP): yo'q")
    phone = str(e.get("phone", "")).strip()
    if phone:
        parts.append(f"telefon: {phone}")
    return ", ".join(p for p in parts if p)


def _format_employee_answer(emps: list[dict[str, Any]]) -> str:
    """Xodim javobini KOD tuzadi, model emas.

    Sabab: modelga qoldirilganda u 16 xodimdan 8 tasini yozib to'xtab qolgan,
    undan oldin esa umuman mavjud bo'lmagan xodimlarni va soxta telefon
    raqamlarini to'qib chiqargan edi. Bank ma'lumotnomasida ro'yxat to'liq va
    aynan bazadagidek bo'lishi shart, shuning uchun uni kod kafolatlaydi."""
    if len(emps) == 1:
        return _format_employee_line(emps[0]) + "."

    depts = {str(e.get("department", "")).strip() for e in emps}
    # Hammasi bitta bo'limdan — bu BO'LIM ro'yxati: har qatorda bo'lim nomini
    # takrorlash keraksiz va "qaysi biri kerak?" deb so'ralmaydi.
    if len(depts) == 1:
        dept = depts.pop()
        lines = [
            f"{i}. {_format_employee_line(e, with_dept=False)}"
            for i, e in enumerate(emps, 1)
        ]
        head = f"{dept} xodimlari ({len(emps)} ta):" if dept else f"Topilgan xodimlar ({len(emps)} ta):"
        return head + "\n\n" + "\n".join(lines)

    # Turli bo'limlardan — bu bir xil ismdagi xodimlar, tanlash kerak.
    lines = [f"{i}. {_format_employee_line(e)}" for i, e in enumerate(emps, 1)]
    return (
        f"Shu so'rov bo'yicha {len(emps)} ta xodim topildi:\n\n"
        + "\n".join(lines)
        + "\n\nQaysi biri kerak? Bo'lim nomini yoki tartib raqamini yozing."
    )


def _match_by_number(
    emps: list[dict[str, Any]], q_lower: str
) -> list[dict[str, Any]]:
    """Savoldagi raqam biror xodimning IP yoki telefoniga ANIQ mos kelsa,
    o'sha xodim(lar)ni qaytaradi. Bu eng kuchli signal — yalang'och "2206"
    ham to'g'ridan-to'g'ri xodimga yo'naladi (mahsulot RAG'iga ketmaydi)."""
    nums = re.findall(r"\d{3,}", q_lower)
    if not nums:
        return []
    ip_targets = {n for n in nums if len(n) <= 5}
    if ip_targets:
        hit = [e for e in emps if str(e.get("ip", "")).strip() in ip_targets]
        if hit:
            return hit
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
    return []


def _name_query_tokens(q_lower: str) -> list[str]:
    """Savoldan ism deb hisoblanishi mumkin bo'lgan so'zlar (qo'shimchasiz)."""
    return [
        s
        for s in (
            _strip_uz_suffix(t)
            for t in _words(_drop_apos(q_lower))
            if len(t) >= 4 and t not in _QUERY_STOP
        )
        if len(s) >= 4 and s not in _QUERY_STOP
    ]


def _score_by_name(
    emps: list[dict[str, Any]], qtokens: list[str]
) -> list[dict[str, Any]]:
    """Ism/familiya bo'yicha eng yaxshi mos kelgan xodim(lar).

    Alohida funksiya, chunki u IKKI joyda kerak: butun bazada qidirishda va
    bo'lim topilgach o'sha bo'lim ICHIDA qidirishda ("IT departamenti
    Shaxzodning ip raqami")."""
    if not qtokens:
        return []
    scored: list[tuple[int, dict[str, Any]]] = []
    qnorms = [_name_norm(qt) for qt in qtokens]
    for e in emps:
        # Otasining ismi (otchestvo) chiqarib tashlanadi — faqat o'z ismi/familiyasi.
        toks = _own_name_tokens(str(e.get("fish", "")))
        score = 0
        for qn in qnorms:
            best_cp = 0
            for nt in toks:
                nn = _name_norm(nt)
                cp = _common_prefix_len(qn, nn)
                # QAT'IY qoida: qisqa so'z uzunining BOSHIGA TO'LIQ tushsin.
                # Ilgari "qisqa so'zning 70% i mos kelsa yetarli" edi va aynan
                # shu narsa eng jirkanch xatoni tug'dirardi: "javob" so'zi
                # "Javohir" ismiga 4 harf bilan mos kelib (4 >= 5*0.7), savol
                # umuman xodim haqida bo'lmasa ham xodim ro'yxati qaytarilardi.
                # Endi: "javob" -> "javohir" RAD (boshi emas), lekin
                # "shaxzod" -> "shaxzodbek" va "xamdamboyev" QABUL.
                if cp >= 4 and cp == min(len(qn), len(nn)):
                    best_cp = max(best_cp, cp)
                # Prefiks bo'lmasa ham: savol so'zi ism bo'lagining ICHIDA
                # to'liq uchrasa hisobga olamiz ("boyev" -> "Xamdamboyev").
                # Kamida 5 belgi — 4 belgili bo'lak tasodifan tushib qolardi.
                elif len(qn) >= 5 and qn in nn:
                    best_cp = max(best_cp, len(qn) - 1)
            score += best_cp
        if score:
            scored.append((score, e))
    if not scored:
        return []
    best = max(s for s, _ in scored)
    return [e for s, e in scored if s == best]


def _match_employees(
    emps: list[dict[str, Any]], q_lower: str
) -> list[dict[str, Any]]:
    """Savolga mos xodimlarni ANIQ moslash bilan topadi: IP raqami, telefon,
    bo'lim nomi yoki F.I.SH bo'yicha. Topilmasa bo'sh ro'yxat."""
    qwords = set(_words(q_lower))

    # 1-2) IP / telefon — aniq raqam moslash (yagona manba: _match_by_number)
    by_number = _match_by_number(emps, q_lower)
    if by_number:
        return by_number

    # 3) Bo'lim nomi — FAQAT savolda aniq xodim-niyat (xodim/ip) bo'lsa. Aks holda
    # filial/manzil so'rovlari ("...bank xizmatlari markazi") xodim bo'limiga
    # noto'g'ri tushib ketardi. Ism qidiruvidan OLDIN turadi, chunki bo'lim nomi
    # tasodifan biror ismning boshiga o'xshab qolishi mumkin.
    # Bo'lim bo'yicha qidiruv ikki holatda ishlaydi:
    #   1) savolda aniq xodim-niyat bor ("xodimlari", "ip raqamlari");
    #   2) savol shunchaki BO'LIM NOMIning o'zi ("IT Departament") — bunda
    #      bo'lim nomining BARCHA ajratuvchi so'zlari savolda bo'lishi shart.
    # Ikkinchisi kerak, chunki foydalanuvchi ko'pincha faqat bo'lim nomini
    # yozadi. Mahsulot savoli tasodifan tushib qolmasligi uchun mahsulot
    # belgisi ("kredit", "karta"...) bo'lgan savol bu yo'lga kiritilmaydi.
    dept_intent = _has_employee_intent(q_lower)
    name_only = not dept_intent and not _has_non_employee_signal(q_lower)
    if dept_intent or name_only:
        # MUHIM: bo'limlar bo'ylab TARTIBLANGAN holda yuramiz va ENG YAXSHI
        # moslikni tanlaymiz. Ilgari tartibsiz set bo'ylab yurib BIRINCHI mos
        # kelgan bo'lim qaytarilardi — shu sabab "IT departamenti xodimlari"
        # so'roviga tasodifan "Moliyaviy hisobotlar departamenti" javob berardi.
        best_dept = ""
        best_dept_score = 0
        for dept in sorted({str(e.get("department", "")) for e in emps}):
            # _QUERY_STOP ham chiqarib tashlanadi. Sabab: bazada "ICHKI AUDIT
            # DEPARTAMENTI" bo'limi bor, "ICHKI raqam" esa ichki raqamni
            # so'rashning odatiy iborasi. "ichki" ni ajratuvchi so'z deb olsak,
            # "Xamdamboyev ichki raqami" kabi HAR QANDAY savol o'sha bo'limga
            # tushib ketardi va butunlay boshqa xodimlar qaytarilardi.
            distinctive = [
                t
                for t in _words(dept)
                if len(t) >= 2
                and not _is_dept_stopword(t)
                and t not in _QUERY_STOP
            ]
            if not distinctive:
                continue
            hits = [t for t in distinctive if _dept_token_hit(t, qwords)]
            if not hits:
                continue
            # Xodim-niyat aytilmagan bo'lsa (savol shunchaki bo'lim nomi) —
            # bo'lim nomining HAMMA ajratuvchi so'zi savolda bo'lishi shart.
            # Qisman moslikka ruxsat bersak, oddiy savol tasodifan biror
            # bo'limga tushib ketardi.
            if not dept_intent and len(hits) < len(distinctive):
                continue
            # Ball: mos so'zlarning umumiy uzunligi (aniqroq moslik = katta ball),
            # ustiga bo'lim nomining necha foizi qamralgani.
            score = sum(len(t) for t in hits) * 10 + (
                100 * len(hits) // len(distinctive)
            )
            if score > best_dept_score:
                best_dept_score = score
                best_dept = dept
        if best_dept:
            dept_emps = [
                e for e in emps if str(e.get("department", "")) == best_dept
            ]
            # Savolda bo'lim BILAN BIRGA ism ham aytilgan bo'lsa ("IT
            # departamenti Shaxzodning ip raqami") — butun bo'limni emas,
            # o'sha bo'lim ichidan ismni qidiramiz.
            named = _score_by_name(dept_emps, _name_query_tokens(q_lower))
            return named or dept_emps

    # 4) F.I.SH — QISMAN moslash: savoldagi so'z ism/familiyaning boshiga mos
    # kelsa yetarli ("Shaxzod" -> "Shaxzodbek", "Jasur" -> "Jasurbek"). Eng ko'p
    # so'zi mos kelgan xodim(lar) qaytariladi — bir nechta bo'lsa hammasi,
    # javobda ro'yxat qilib "qaysi biri kerak?" deb so'raladi.
    #
    # MUHIM: savol aniq mahsulot/filial haqida bo'lsa (va xodim-niyat
    # bildirilmagan bo'lsa) bu bosqich UMUMAN ishlamaydi — aks holda oddiy
    # so'zlar tasodifan ismga mos kelib, "qaysi filial yaqin" savoliga
    # xodimlar ro'yxati qaytarilardi.
    if _has_non_employee_signal(q_lower) and not _has_employee_intent(q_lower):
        return []

    return _score_by_name(emps, _name_query_tokens(q_lower))


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
    # Avtokreditlar ro'yxatida HAR bandda bor — ilgari "AvtoSelf 2.0
    # Avtokrediti" deb yozilganda shu so'z "Roodell avto Avtokrediti" ga ham
    # mos kelib, noto'g'ri band tanlanardi.
    "avtokrediti", "avtokredit",
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


# Ro'yxatdan tanlash javobi QISQA bo'ladi: "3", "Uzcard", "Visa Gold",
# "Sirdaryo bank xizmatlari markazi". Undan uzun jumla — bu tanlov emas,
# savol. Umumiy so'zlar (_LIST_MATCH_STOPWORDS) olib tashlangandan keyingi
# so'zlar soni shundan oshsa, tanlov deb hisoblamaymiz.
_MAX_CHOICE_WORDS = 5

# Foydalanuvchi bizni TUZATAYOTGAN bo'lsa — bu ham tanlov emas. Aynan shu
# yerda og'ir xato bo'lgan: "Uzcard tizimi haqida so'rayapman, Uzcard kartasi
# haqida so'ramadim" degan tuzatish "Uzcard" bandini tanlash deb qabul
# qilinib, router UMUMAN chaqirilmasdi va foydalanuvchi aynan o'zi rad etgan
# javobni QAYTA olardi.
_CORRECTION_MARKERS = (
    "soramadim", "demadim", "aytmadim", "tushunmading", "tushunmadingiz",
    " emas", "boshqa narsa",
)

# Ro'yxat tanlovi ro'yxat berilgandan keyin DARROV keladi. Butun tarixni
# oxirigacha titish xato: suhbat boshidagi eski ro'yxat bilan hozirgi savol
# tasodifan mos kelib qolardi.
_LIST_LOOKBACK_TURNS = 3


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
    if want_num is None:
        # Nom bilan tanlash — faqat QISQA va tuzatish bo'lmagan xabarda.
        # Raqam bilan tanlashga ("3") bu shartlar kerak emas: u aniq tanlov.
        if len(q_words) > _MAX_CHOICE_WORDS:
            return None
        flat = re.sub(r"['ʻʼ`’]", "", to_latin(question).lower())
        if any(m in flat for m in _CORRECTION_MARKERS):
            return None

    seen_assistant = 0
    for turn in reversed(history):
        if turn.role != "assistant":
            continue
        seen_assistant += 1
        if seen_assistant > _LIST_LOOKBACK_TURNS:
            break
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

        # Bandning nomi AYNAN ko'chirib yozilgan bo'lsa (qo'shtirnoq, registr
        # farqi hisobga olinmaydi) — taxminiy solishtirishga hojat yo'q.
        q_norm = " ".join(_words(to_latin(question)))
        for _, text in items:
            cleaned = to_latin(text.strip().strip("*").strip())
            if q_norm and " ".join(_words(cleaned)) == q_norm:
                return cleaned

        # Raqam emas — bandning NOMI bilan yozgan bo'lishi mumkin. ENG YAXSHI
        # mos kelgan bandni tanlaymiz (birinchi mos kelganini emas) — aks
        # holda tasodifiy 1-so'zlik moslik (masalan boshqa bandning nomi)
        # haqiqiy tanlovdan OLDIN kelib qolsa, noto'g'ri band qaytardi.
        # Baho (kattasi yaxshi):
        #   1) foydalanuvchi so'zlarining QANCHA QISMI band nomida bor
        #      (qisqa so'zlar ham: "Kelajak UYI" — "Kelajak" ta'lim krediti
        #      emas, "Kelajak uyi" ipotekasi);
        #   2) shulardan nechtasi AYNAN (prefiks emas) mos kelgan — "avto"
        #      "Roodell AVTO" da aynan bor, "AVTOself" da faqat prefiks;
        #   3) band nomining QANCHA QISMI mos kelgan;
        #   4) mos so'zlar soni.
        # Ilgari faqat 4) sanalardi va durangda ro'yxatdagi BIRINCHI band
        # tanlanardi: "AvtoSelf 2.0" uchun "Roodell avto" (2-band) qaytgan edi.
        # Endi durang bo'lsa ("Kelajak" — ta'lim krediti ham, "Kelajak uyi"
        # ham) hech biri tanlanmaydi: savol routerga o'tadi.
        scored: list[tuple[tuple[float, int, float, int], str, bool]] = []
        for _, text in items:
            cleaned = to_latin(text.strip().strip("*").strip())
            name_words = [
                w for w in _words(cleaned)
                if len(w) >= 3 and w not in _LIST_MATCH_STOPWORDS
            ]
            toks = [w for w in name_words if len(w) >= 4]
            q_cov = sum(
                1 for qw in q_words
                if any(qw == w or _prefix_match(w, qw) for w in name_words)
            ) / len(q_words)
            q_exact = sum(1 for qw in q_words if qw in name_words)
            hits = sum(1 for t in toks if any(_prefix_match(t, qw) for qw in q_words))
            # Qisqa (1-2 so'zlik) nomda BARCHA so'z mos kelishi shart —
            # bitta tasodifiy prefiks moslikdan xato band tanlanmasin.
            need = len(toks) if len(toks) <= 2 else len(toks) - 1
            by_name = bool(toks) and hits >= need
            if by_name or q_cov == 1.0:
                ratio = hits / len(toks) if toks else 0.0
                scored.append(((q_cov, q_exact, ratio, hits), cleaned, by_name))
        if not scored:
            return None
        scored.sort(key=lambda s: s[0], reverse=True)
        best_score, best, best_by_name = scored[0]
        if len(scored) > 1 and scored[1][0] == best_score:
            return None
        if best_by_name:
            return best
        # Faqat "yozilgan so'zlarning hammasi bor" sharti bilan o'tgan band
        # ("Roodell", "tez pul") — u YAGONA bo'lsagina tanlanadi.
        full = [s for s in scored if s[0][0] == 1.0]
        return best if len(full) == 1 else None
    return None


def _mentions_catalog_title(q_lower: str, titles: list[str]) -> bool:
    """Savolda bazadagi biror MAHSULOT/FILIAL nomi tilga olinganmi.

    Kerak, chunki joy nomi tasodifan xodim ismining boshiga mos kelib qolishi
    mumkin ("Yunusobod" -> "... YUNUS o'g'li") va savol filial haqida bo'lsa ham
    xodim ma'lumotnomasiga tushib ketardi. Nom bazadagi sarlavhaga mos kelsa —
    bu mahsulot savoli, xodim qidiruvi umuman ishga tushmaydi.

    _prefix_match ishlatiladi — bazadagi imlo saytdan qanday kelgan bo'lsa
    shunday ("Yunusubod"), foydalanuvchi esa boshqacha yozishi mumkin."""
    qwords = [
        w
        for w in _words(q_lower)
        if len(w) >= 4 and w not in _LIST_MATCH_STOPWORDS and w not in _QUERY_STOP
    ]
    if not qwords:
        return False
    for title in titles:
        toks = [
            w
            for w in _words(to_latin(title))
            if len(w) >= 4 and w not in _LIST_MATCH_STOPWORDS
        ]
        if any(_prefix_match(t, qw) for t in toks for qw in qwords):
            return True
    return False


def _localize(text: str, lang: ReplyLang) -> str:
    """Tayyor (modelsiz) javobni foydalanuvchi tiliga keltiradi.

    Ilgari faqat alifbo hisobga olinardi (`to_cyrillic`), ya'ni ruscha
    savolga o'zbekcha matn kirill harflarida qaytardi. Ruschasi yo'q matn
    (RU_CANNED_REPLIES da kaliti yo'q) o'zbek lotinida qoladi — harf-baharf
    kirillga o'girilgan o'zbekcha rus o'quvchisi uchun baribir tushunarsiz."""
    if lang == "ru":
        return RU_CANNED_REPLIES.get(text, text)
    if lang == "uz_cyrl":
        return to_cyrillic(text)
    return text


def _router_reply(reply: str, lang: ReplyLang) -> str:
    """Salomlashish / bot haqidagi savolga router yozgan javob.

    Router prompti o'zbekcha va unga til bloki qo'shilmaydi, shuning uchun
    model ruscha "Здравствуйте" ga ham "Assalomu alaykum" deb yozib qo'yardi.
    Ruscha savolga ruscha bo'lmagan javob kelsa — tayyor ruscha matn."""
    if not reply or (lang == "ru" and not is_russian_text(reply)):
        return _localize(SMALLTALK_FALLBACK_REPLY, lang)
    return to_cyrillic(reply) if lang == "uz_cyrl" else reply


def _bot_reply(decision: Route, history: list[ChatTurn] | None, lang: ReplyLang) -> str:
    """Salomlashish va bot haqidagi savolga javob.

    "Sen nimasan / nima qila olasan" (ABOUT_BOT) va suhbatning BIRINCHI
    salomiga — bot va ilovadagi vositalar ro'yxati (CAPABILITIES_REPLY).
    Suhbat o'rtasidagi "rahmat", "xayr" kabi gapga esa routerning qisqa
    javobi: har safar uzun ro'yxat chiqsa bezor qiladi."""
    if decision.intent is Intent.ABOUT_BOT:
        return _localize(CAPABILITIES_REPLY, lang)
    if not history:
        greeting = "Здравствуйте!" if lang == "ru" else _localize("Assalomu alaykum!", lang)
        body = _localize(CAPABILITIES_REPLY, lang)
        return f"{greeting} {body}"
    return _router_reply(decision.reply, lang)


def _guard_input(
    question: str, history: list[ChatTurn] | None
) -> tuple[str, list[ChatTurn] | None, bool]:
    """Modelga ketishdan oldin: savol va foydalanuvchining oldingi
    xabarlaridagi PII maskalanadi; savolda ochiq prompt-injection bo'lsa
    `blocked=True` (javob modelsiz qaytariladi).

    Faqat JORIY savol injection uchun tekshiriladi — tarixdagi eski xabar
    tufayli butun suhbat bloklanib qolmasin (tarix baribir SECURITY_RULES
    ostida "ma'lumot" sifatida o'qiladi)."""
    if looks_like_injection(question):
        logger.warning("Prompt-injection urinishi bloklandi: %r", question[:200])
        return question, history, True
    masked, kinds = mask_pii(question)
    if kinds:
        logger.info("Savolda PII maskalandi: %s", ",".join(kinds))
    if history:
        history = [
            ChatTurn(role=t.role, content=mask_pii(t.content)[0])
            if t.role == "user"
            else t
            for t in history
        ]
    return masked, history, False


# Veb-qidiruvga faqat bank faktiga oid niyatlar boradi. Xodim (shaxsiy
# ma'lumot), suhbat tarixi, salomlashish, soha tashqarisi — hech qachon.
_WEB_INTENTS = frozenset({Intent.PRODUCT, Intent.RATES, Intent.BRANCH, Intent.CONCEPT})


def _web_eligible(decision: Route | None, question: str) -> bool:
    if not config.web_search.WEB_SEARCH_ENABLED:
        return False
    if decision is None or decision.intent not in _WEB_INTENTS:
        return False
    if _has_employee_intent(question.lower()) or _is_meaningless_query(question):
        return False
    return True


def _web_prompt(question: str, hits: list["web_search.WebHit"]) -> str:
    pages = "\n\n".join(
        f"[{i}] {h.title} ({h.url})\n{h.text}" for i, h in enumerate(hits, 1)
    )
    # Bugungi sana — model eski press-relizni "hozirgi" deb bermasin
    today = (get_utc_now() + timedelta(hours=5)).date().isoformat()
    return f"TODAY: {today}\n\nPAGES:\n{pages}\n\nSAVOL: {question}"


def _web_sources(hits: list["web_search.WebHit"]) -> list[SourceRef]:
    return [SourceRef(title=h.title, score=0.0, url=h.url, kind="web") for h in hits]


def _is_web_lookup(text: str) -> bool:
    """Concept javobi "internetdan qidir" signalimi (NEEDS_WEB)."""
    return text.strip().strip(".").upper().startswith(WEB_LOOKUP_TOKEN)


def _is_web_not_found(text: str) -> bool:
    return text.strip().strip(".").upper().startswith(WEB_NOT_FOUND_TOKEN)


def _with_lang(system: str, lang: ReplyLang) -> str:
    """Ruscha savolda system prompt oxiriga til almashtirish blokini qo'shadi
    (qara: prompts.RU_REPLY_OVERRIDE).

    Til savollarida (LANGUAGE_SYSTEM) blok BOSHQA: umumiysi "butun javobni
    ruscha yoz" deydi va tarjimaga berilgan ruscha matn o'zbekchaga emas,
    yana ruschaga "tarjima" bo'lib qaytardi (qara: RU_LANGUAGE_OVERRIDE)."""
    # Xavfsizlik qoidasi har doim ENG OXIRIDA — model oxirgi ko'rsatmaga
    # ko'proq quloq soladi (qara: prompts.SECURITY_RULES)
    if lang != "ru":
        return system + SECURITY_RULES
    if system is LANGUAGE_SYSTEM:
        return system + RU_LANGUAGE_OVERRIDE + SECURITY_RULES
    return system + RU_REPLY_OVERRIDE + SECURITY_RULES


def _blind_employee_guess(decision: Route | None, question: str) -> bool:
    """Router YIQILGAN (qaror yo'q) va savolda xodimga oid aniq belgi ham yo'q.

    Bu holda ism bo'yicha xodim qidiruvini ochmaymiz. Xodim yo'li routerni
    "maslahatchi" deb biladi va yalang'och familiyani ham qidiradi — router
    ishlaganda bu to'g'ri, chunki "concept"/"language" kabi niyatlar undan
    oldin qaytib ketadi. Router yiqilganda esa har qanday savol shu yerga
    tushardi: "mutolaa so'zining ma'nosi nima" savolidagi so'z xodim
    familiyasiga prefiks bo'yicha o'xshab, foydalanuvchi tasodifiy xodimning
    telefonini olgan. Raqam ("2206") yoki "xodim/ip" so'zi bo'lsa — qidiruv
    baribir ochiladi, u yerda moslik aniq."""
    if decision is not None:
        return False
    q_lower = question.lower()
    return not _has_employee_intent(q_lower) and not re.search(
        r"\b\d{3,5}\b", q_lower
    )


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


# "Xodim" so'zining o'zaklari — SO'Z BOSHIDAN qidiriladi ("xodimlar",
# "ходимлари", "сотрудники" mos keladi). Ilgari matnning istalgan joyidan
# qidirilardi va ruscha "необХОДИМо" so'zi "ходим" ga mos kelib, tarjimaga
# berilgan ruscha matn xodim qidiruviga ketib qolardi ("сотрудник не найден").
_EMPLOYEE_WORD_STEMS = ("xodim", "hodim", "ходим", "сотрудник")
# Ko'p so'zli belgilar — bularda tasodifiy moslik xavfi yo'q
_EMPLOYEE_PHRASES = (
    "ichki raqam",
    "ички рақам",
    "внутренний номер",
    "внутреннего номер",
)
# Xodim haqidagi savol doim QISQA ("1036 kimniki", "IT bo'limi xodimlari").
# Bundan uzun matn — odatda tarjima/tahrir uchun tashlangan hujjat; unda
# "IP", "сотрудник" kabi so'z uchragani xodim so'rovi degani emas. Bunday
# matnni kalit so'z bilan xodim yo'liga MAJBURLAMAYMIZ (router o'zi hal qiladi).
_EMPLOYEE_HINT_MAX_CHARS = 200


def _mentions_employee_word(words: set[str]) -> bool:
    return any(w.startswith(_EMPLOYEE_WORD_STEMS) for w in words)


def _has_employee_intent(q_lower: str) -> bool:
    """Savol aniq XODIMLAR haqidami — bo'lim bo'yicha yo'naltirishni faqat shunda
    yoqamiz. Aks holda "Toshkent shahar BANK xizmatlari markazi" kabi filial nomi
    xodim bo'limiga (masalan "Bank karta...") noto'g'ri tushib ketardi."""
    if len(q_lower) > _EMPLOYEE_HINT_MAX_CHARS:
        return False
    words = set(_words(q_lower))
    if "ip" in words:
        return True
    # Ruscha belgilar ham bor: ruscha savol lotinga o'girilmaydi (execute_stream)
    if _mentions_employee_word(words) or any(p in q_lower for p in _EMPLOYEE_PHRASES):
        return True
    # "2206 kimniki", "2213 kimga tegishli" — savolda "ip" so'zi yo'q, lekin
    # 3-5 xonali raqam + "kim/tegishli/egasi" bu aniq ichki raqam so'rovi.
    # Busiz bunday savol mahsulot RAG'iga ketib, "ma'lumot topilmadi" derdi.
    whose = (
        any(w.startswith("kim") for w in words)
        or "tegishli" in words
        or "egasi" in words
    )
    return bool(whose and re.search(r"\b\d{3,5}\b", q_lower))


# "Kim qaraydi / kim mas'ul / kimga murojaat" — admin qo'ygan KALIT SO'Z
# bo'yicha xodim qidiruvi faqat shunday savolda ochiladi. Aks holda "EDO da
# hujjat qanday yuboriladi" kabi oddiy savol ham yo'riqnoma o'rniga xodimni
# qaytarardi. Apostrofsiz va lotinda (_text_words shunday qaytaradi; ruscha
# "кто/отвечает" ham lotinga o'giriladi).
_RESPONSIBLE_STEMS = (
    "kim", "qaray", "masul", "javobgar", "shugullan", "murojaat", "boglan",
    "kto", "otvecha", "zanima",
)
# Savol faqat ichki raqamning o'zi: "2206" yoki "2206?"
_BARE_IP_RE = re.compile(r"\s*\d{3,4}\s*\??\s*")


def _keyword_hit(keyword: str, qwords: set[str]) -> bool:
    """Kalit so'zning HAR bir so'zi savolda bor (qo'shimcha bilan ham:
    "edo" ~ "edoga", "ip" ~ "iplarga")."""
    toks = _text_words(keyword)
    return bool(toks) and all(
        any(w == t or (w.startswith(t) and _is_suffix_tail(w[len(t):])) for w in qwords)
        for t in toks
    )


_MANBA_PAREN_RE = re.compile(r"\s*\(\s*manba\s*:?[^)]*\)", re.IGNORECASE)
_DUP_URL_RE = re.compile(r"(https?://\S+?)\1+")


def _dedupe_source_links(text: str) -> str:
    """Model ba'zan kontekstdagi manba havolasini javobga ikki marta ko'chiradi
    ("Batafsil: url(Manba: url)"). Prompt buni taqiqlaydi, lekin kafolat uchun
    bu yerda ham tozalaymiz: "(Manba: ...)" qavsli qismini va ketma-ket
    takrorlangan bir xil URL'ni olib tashlaymiz."""
    text = _MANBA_PAREN_RE.sub("", text)
    text = _DUP_URL_RE.sub(r"\1", text)
    return text


def _is_meaningless_query(text: str) -> bool:
    """Savolda birorta ham harf yo'q (masalan "000000000000", "-----") —
    bunday so'rov mahsulot/xodim yo'nalishidan o'tib kelgan bo'lsa, bu bema'ni
    kiritma; embedding qidiruviga bermasdan darrov "ma'lumot yo'q" qaytaramiz
    (uzoq LLM chaqiruvining oldini oladi)."""
    return not any(ch.isalpha() for ch in text)


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


def _clean_concept_answer(text: str) -> str:
    """Umumiy (soha) javobidan mahsulot javobiga tegishli qoldiqlarni oladi.

    CONCEPT_SYSTEM havola va yopiluvchi savolni TAQIQLAYDI, lekin model
    ba'zan baribir qo'shib yuboradi — bu javob bazadan olinmagan, ya'ni
    havola qayerdan kelgani noma'lum (model o'ylab topgan URL bo'lishi ham
    mumkin). Shuning uchun kod tarafida ham tozalaymiz."""
    lines = [
        ln
        for ln in text.split("\n")
        if not ln.strip()
        .lower()
        .startswith(("batafsil:", "manba:", "source_url:", "подробнее:"))
    ]
    # Oxiridagi "Yana qaysi ... beray?" / "Shu turlardan qaysi biri..." savoli
    while lines:
        low = lines[-1].lower().strip()
        if not low:
            lines.pop()
            continue
        if ("qaysi biri" in low or "qaysi karta" in low or "qaysi kredit" in low) and (
            "beray" in low or "kerak?" in low
        ):
            lines.pop()
            continue
        break
    return "\n".join(lines).strip()


class _ConceptLineFilter:
    """Oqim (stream) uchun _clean_concept_answer ning ekvivalenti.

    Javob token-token kelgani uchun tayyor matnni tozalab bo'lmaydi. Bu filtr
    QATOR BOSHINI kuzatadi: qator taqiqlangan prefiksdan boshlansa, o'sha
    qatorni oxirigacha o'tkazmaydi. Qaror qator boshidagi bir necha belgidan
    keyin qabul qilinadi, shuning uchun oqim sezilarli kechikmaydi."""

    _BAD = (
        "batafsil:",
        "manba:",
        "source_url:",
        "yana qaysi",
        "shu turlardan",
        # Ruscha javobdagi ekvivalentlar (RU_REPLY_OVERRIDE)
        "подробнее:",
        "по какому ещё",
    )

    def __init__(self) -> None:
        # Qator boshi — taqiqli prefiksmi yoki yo'qmi, hali aniq emas
        self._pending = ""
        self._at_line_start = True
        self._dropping = False

    def feed(self, chunk: str) -> str:
        out: list[str] = []
        for ch in chunk:
            if self._dropping:
                # Taqiqli qator — satr oxirigacha hammasi tashlanadi
                if ch == "\n":
                    self._dropping = False
                    self._at_line_start = True
                continue
            if not self._at_line_start:
                out.append(ch)
                if ch == "\n":
                    self._at_line_start = True
                continue
            self._pending += ch
            if ch == "\n":
                out.append(self._pending)
                self._pending = ""
                continue
            low = self._pending.lstrip().lower()
            if any(low.startswith(bad) for bad in self._BAD):
                self._pending = ""
                self._dropping = True
                continue
            if any(bad.startswith(low) for bad in self._BAD):
                # Hali ham taqiqli prefiks bo'lishi mumkin — kutamiz
                continue
            out.append(self._pending)
            self._pending = ""
            self._at_line_start = False
        return "".join(out)

    def flush(self) -> str:
        rest, self._pending = self._pending, ""
        return "" if self._dropping else rest


def _is_generic_employee_request(q_lower: str) -> bool:
    """"Xodimlar raqamlari" kabi umumiy (aniq xodim/bo'limsiz) so'rovmi —
    aniqlashtirishni so'rash uchun."""
    has_emp = _mentions_employee_word(set(_words(q_lower)))
    has_num = any(
        w in q_lower for w in ("raqam", "ip", "telefon", "рақам", "телефон")
    )
    return has_emp and has_num and len(_words(q_lower)) <= 5


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


# Apostrof bir necha xil belgi bilan yoziladi: telefon klaviaturasi tipografik
# ‘ ’ ni qo'yadi, kodda esa ASCII ' turadi. Ular solishtirishda mos kelmay,
# "o'tkazma" kabi kalit so'z topilmay qolardi.
_APOSTROPHE_MAP = dict.fromkeys(map(ord, "‘’ʻʼ`´"), "'")


def _norm_apostrophes(s: str) -> str:
    return s.translate(_APOSTROPHE_MAP)


# Mahsulot nomlarida qo'shtirnoq bor va u har xil: "Tez pul", “Green Avto”,
# «Sayohat». Foydalanuvchi ham ro'yxatdan nusxa ko'chirib yuboradi. Nom
# solishtirishda ular butunlay olib tashlanadi.
_QUOTE_MAP = dict.fromkeys(map(ord, "«»“”„‟\"'‘’ʻʼ`´"), " ")


def _norm_for_match(s: str) -> str:
    """Nom solishtirish uchun: qo'shtirnoq/apostrofsiz, bir bo'shliqli."""
    return " ".join(s.translate(_QUOTE_MAP).lower().split())


# --- Filial HUDUDI ------------------------------------------------------- #
# Ilgari filial ro'yxati savoldagi "qo'shimcha so'zlar" bo'yicha filtrlanardi:
# so'z filial matnida uchrasa mos deb hisoblanardi va filtrlar OR bilan
# birlashardi. Ikkita jiddiy xato shundan chiqardi:
#   1) "Toshkent viloyatida qaysi BXM JOYLASHGAN" so'rovida "joylashgan" so'zi
#      deyarli har bir filial manzilida uchraydi — butun ro'yxat "mos" bo'lib
#      qolardi;
#   2) Farg'ona viloyatidagi ofis manzilida "TOSHKENT ko'chasi" bo'lgani uchun
#      u ham Toshkent so'roviga tushardi.
# Endi so'z moslash o'rniga hudud MA'LUMOTNING O'ZIDAN ajratiladi: manzil doim
# "<Hudud> viloyati, ..." yoki "<Hudud> shahri, ..." bilan boshlanadi. Ko'cha
# nomi bu qolipga tushmaydi va endi shovqin qilmaydi.
_ADMIN_RE = re.compile(
    r"([a-z'\-]{4,})\s+(viloyat|shahar|shahr|shaxar|shaxr)\w*", re.IGNORECASE
)


def _admin_level(word: str) -> str:
    """Daraja: "viloyat" yoki "shahar" (transliteratsiya farqidan qat'i nazar)."""
    return "viloyat" if word.lower().startswith("viloyat") else "shahar"


def _region_key(name: str) -> str:
    """Hudud nomini solishtirish uchun: apostrof/defissiz, kichik harflarda
    ("Farg'ona" va "Fargona" bir xil kalitga tushsin)."""
    return re.sub(r"['\-]", "", name.lower())


def _region_of(text: str) -> tuple[str, str, str]:
    """Matndagi BIRINCHI hudud ko'rsatkichi: (kalit, daraja, ko'rinadigan nom).
    Topilmasa — bo'sh satrlar."""
    m = _ADMIN_RE.search(_norm_apostrophes(to_latin(text)))
    if not m:
        return "", "", ""
    return _region_key(m.group(1)), _admin_level(m.group(2)), m.group(1)


# Filiallar RO'YXATI / joylashuvi so'ralganda uchraydigan so'z o'zaklari.
# Savolda bulardan, hudud nomidan va _BROAD_QUESTION_STOPWORDS dan boshqa
# mazmunli so'z bo'lsa — bu ro'yxat so'rovi emas.
_BRANCH_LIST_STEMS = (
    "filial", "bxm", "bank", "xizmat", "markaz", "ofis", "royxat", "joylash",
    "manzil", "qayer", "hudud", "viloyat", "shahar", "shahr", "tuman", "nechta",
    "soni", "barcha", "hamma", "korsat",
)


def _branch_other_topic(q: str, items: list[tuple[str, str]]) -> bool:
    """Filial so'zi bor savol ro'yxatdan BOSHQA narsani so'rayaptimi.

    "Toshkentdagi filiallar", "filiallar ro'yxati", "Samarqand viloyatida
    qaysi BXM joylashgan" — ro'yxat (False). "Filiallar tarmog'ini
    kengaytirish bo'yicha yangi rejalari qanday" — boshqa mavzu (True):
    ilgari bunga 60+ filial ro'yxati qaytarilgan edi."""
    regions = {_region_of(f"{t} {x}")[0] for t, x in items} - {""}
    for w in _words(q.replace("'", "")):
        if len(w) < 4 or w in _BROAD_QUESTION_STOPWORDS:
            continue
        if w.startswith(_BRANCH_LIST_STEMS):
            continue
        if any(_region_key(w).startswith(r[:5]) for r in regions):
            continue
        return True
    return False


def _question_region(question: str, known: set[str]) -> tuple[str, str]:
    """Savolda qaysi hudud so'ralganini aniqlaydi: (kalit, daraja).

    Hudud nomi BAZADA mavjud bo'lishi shart — shu sabab "qaysi viloyatda"
    savolidagi "qaysi" hudud deb qabul qilinmaydi. Daraja aytilmagan bo'lsa
    ("Samarqanddagi filiallar") ikkinchi qiymat bo'sh qoladi va daraja
    bo'yicha toraytirish qilinmaydi."""
    norm = _norm_apostrophes(to_latin(question))
    m = _ADMIN_RE.search(norm)
    if m:
        key = _region_key(m.group(1))
        if key in known:
            return key, _admin_level(m.group(2))
    # Daraja aytilmagan — savol so'zlarini bazadagi hudud nomlariga solishtiramiz.
    # sorted(): bir nechta hudud mos kelib qolsa natija barqaror bo'lsin.
    for w in _words(norm.replace("'", "")):
        if len(w) >= 4:
            for r in sorted(known):
                if _prefix_match(w, r):
                    return r, ""
    return "", ""


# Savol shunchaki ro'yxat emas, MASLAHAT/TAVSIYA so'rayotganini bildiruvchi
# belgilar. Bunday savolga tayyor ro'yxat tashlash noto'g'ri — modelga berib,
# mahsulotlarni solishtirib tavsiya qildiramiz.
_ADVICE_MARKERS = (
    "tavsiya", "maslahat", "eng yaxshi", "yaxshiroq", "arzon", "qulay",
    "foizi past", "past foiz", "eng past", "eng kam", "solishtir", "farqi",
    "qaysi biri yaxshi", "olmoqchi", "olsam", "sotib ol", "kerakmi",
    "mos keladi", "nima farq", "tanla",
)


def _asks_for_advice(q_lower: str) -> bool:
    return any(m in q_lower for m in _ADVICE_MARKERS)


# Turkum nomi (— _category_label qaytaradigan label bilan AYNAN mos kelishi
# shart) -> savolda uchrashi mumkin bo'lgan kalit so'zlar. _broad_category_reply
# shu asosida savol qaysi turkum haqida ekanini aniqlaydi.
# Filiallar turkumi alohida ajratilgan: faqat unda deterministik (hudud
# bo'yicha) toraytirish qo'llanadi — pastdagi _broad_category_reply'ga qarang.
_BRANCH_LABEL = "Filiallar (bank xizmatlari markazlari va ofislari)"

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Bank kartalari": ("karta",),
    "Kreditlar": ("kredit", "ipoteka", "qarz", "mikroqarz", "mikrokredit"),
    "Omonatlar": ("omonat", "depozit"),
    "Pul o'tkazmalari": ("o'tkazma", "otkazma", "o'tkazish", "otkazish"),
    _BRANCH_LABEL: (
        "filial",
        "bxm",
        "bank xizmatlari markazi",
        "bank xizmatlari ofisi",
    ),
}

# Turkumning O'ZINI bildiruvchi so'zlar — yuqoridagi ro'yxatdan FARQ QILADI.
# _CATEGORY_KEYWORDS turkumni ANIQLASH uchun ("ipoteka" so'zi ham kreditlar
# turkumiga ishora qiladi), bu esa turkum ichida TORAYTIRISHDA e'tiborga
# olinmaydigan so'zlar. "ipoteka", "avtokredit", "mikroqarz" bu yerda YO'Q —
# ular kredit TURI, ya'ni haqiqiy filtr. Aynan shuning uchun "Ipoteka
# kreditlari bo'yicha ma'lumot ber" so'roviga barcha 20 ta kredit qaytarilardi.
_CATEGORY_GENERIC: dict[str, tuple[str, ...]] = {
    "Bank kartalari": ("karta",),
    "Kreditlar": ("kredit",),
    "Omonatlar": ("omonat", "depozit"),
    "Pul o'tkazmalari": ("otkazma", "otkazish"),
}


# --- ANIQLASHTIRISH (savol berib olish) --------------------------------- #
# Savolda bazadagi mahsulot nomining faqat BIR QISMI aytilgan bo'lishi mumkin
# ("meros" -> «Meros omonati»). Ilgari bunday savol router tomonidan "umumiy
# tushuncha" deb baholanib, bazaga UMUMAN borilmasdi va bot "bank tizimida
# bunday mahsulot yo'q" deb javob berardi — bazada esa u bor edi. Endi bunday
# holatda javob to'qilmaydi, foydalanuvchidan aniqlashtirib so'raladi.
_CLARIFY_MAX_OPTIONS = 3
# Aniqlashtirish savolimizni keyinchalik tanib olish uchun belgi (foydalanuvchi
# "ha" deb javob berganda). Oddiy mahsulot javobida ham «...» uchraydi
# («Sayohat» mikroqarzi), shuning uchun faqat tirnoqqa tayanib bo'lmaydi.
_CLARIFY_MARKER = "Aniqlashtirib olay"
_CLARIFY_TITLE_RE = re.compile(r"«([^«»\n]{2,120})»")
_AFFIRMATIVE_WORDS = frozenset(
    {"ha", "xa", "aha", "shu", "shuni", "shunisi", "aynan", "togri", "yes", "da"}
)
# Turkum so'zi ("kredit", "omonat", "karta") o'ziga xos belgi EMAS: u o'nlab
# mahsulot nomida bor. Faqat shu so'z mos kelgani uchun aniqlashtirish
# so'ralsa, "kredit foizi qanday hisoblanadi" kabi umumiy savolga ham
# keraksiz qayta savol berilardi.
_GENERIC_TITLE_WORDS = frozenset(
    w for words in _CATEGORY_KEYWORDS.values() for w in words
) | {
    "krediti",
    "kreditlari",
    "kartasi",
    "kartalari",
    "omonati",
    "omonatlar",
    "bank",
    "banki",
    "turonbank",
    # Yordamchi so'zlar: o'zi hech narsani anglatmaydi. "Markaziy bank qaysi
    # banklar BILAN hamkorlik qiladi" savoli «Biz bilan bog'lanish» sahifasiga
    # qisman mos kelib, bot "shu sahifa haqidami?" deb so'rab qolgan edi.
    "bilan",
    "biz",
    "siz",
    "uchun",
    "haqida",
    "orqali",
    "yicha",
    "qanday",
    "qaysi",
    "qancha",
    "nima",
    "kabi",
    "yoki",
    "lanish",
    "dlya",
    "kak",
    "chto",
}


# Savol MAHSULOT haqida emas, balki TASHKILOT/brend haqida ekanini bildiruvchi
# so'z o'zaklari ("Mastercard kompaniyasi qachon tashkil topgan"). Ilgari
# bunday savolda "mastercard" so'zi karta nomlariga qisman mos kelib, bot
# «MasterCard Gold» va h.k. dan birini tanlashni so'rardi. So'z o'zagi bilan
# tekshiriladi: "kompaniyasichi", "tashkil", "osnovana" ham tushadi.
_ORG_QUESTION_STEMS = (
    "kompaniya",
    "korporatsiya",
    "tashkil",
    "asoschi",
    "asoslan",
    "tarix",
    "shtab",
    "osnova",
    "istori",
    "korporaci",
)


def _asks_about_organization(question: str) -> bool:
    """Savol kompaniya/brendning o'zi (tarixi, asoschisi, tashkil topgani)
    haqidami — bunda bazadagi mahsulot nomlari bilan solishtirilmaydi."""
    words = _words(_norm_for_match(_norm_apostrophes(to_latin(question).lower())))
    return any(w.startswith(_ORG_QUESTION_STEMS) for w in words)


# Foydalanuvchi mahsulotni emas, so'zning UMUMIY ma'nosini so'rayotganini
# o'zi aytgan ("yo'q, umuman meros nima"). Aniqlashtirish matnimiz aynan
# "umumiy tushuncha bo'lsa, to'liqroq yozing" deydi — shu belgini tanimasak,
# to'liqroq yozilgan savolga ham yana o'sha savol qaytardi.
_GENERAL_MEANING_STEMS = ("umum", "tushuncha", "atama", "voobs", "ponyati", "termin")
_GENERAL_MEANING_PARTS = ("ma'no", "ta'rif")


def _asks_general_meaning(question: str) -> bool:
    text = _norm_apostrophes(to_latin(question).lower())
    if any(part in text for part in _GENERAL_MEANING_PARTS):
        return True
    return any(w.startswith(_GENERAL_MEANING_STEMS) for w in _words(text))


def _last_turn_was_clarify(history: list[ChatTurn] | None) -> bool:
    """Oxirgi bot javobi aniqlashtiruvchi savol bo'lganmi.

    Foydalanuvchi variant tanlamay, savolini to'liqroq qayta yozgan bo'lsa
    (biz aynan shuni so'raganmiz), ikkinchi marta aniqlashtirish so'ralmaydi —
    aks holda bot bir xil savolni cheksiz takrorlardi."""
    if not history:
        return False
    last = next((t for t in reversed(history) if t.role == "assistant"), None)
    return last is not None and (
        _CLARIFY_MARKER.lower() in to_latin(last.content).lower()
    )


def _declined_clarify_titles(history: list[ChatTurn] | None) -> set[str]:
    """Suhbatda aniqlashtirish so'ralib, foydalanuvchi MAHSULOTNI TANLAMAGAN
    (umumiy ma'noni so'ragan) nomlar.

    "Meros nima" -> aniqlashtirish -> "meros tushunchasi haqida" -> umumiy
    javob -> "meros farzandlar orasida teng bo'linadimi?" — oxirgi savolda
    ham "meros" so'zi bor va ilgari yana o'sha aniqlashtirish qaytardi.
    Foydalanuvchi bir marta "mahsulot emas" deganini suhbat davomida eslaymiz."""
    if not history:
        return set()
    declined: set[str] = set()
    for i, turn in enumerate(history):
        if turn.role != "assistant":
            continue
        if _CLARIFY_MARKER.lower() not in to_latin(turn.content).lower():
            continue
        reply = next((t for t in history[i + 1 :] if t.role == "user"), None)
        if reply is None:
            continue
        if _resolve_clarification(reply.content, history[: i + 1]) is None:
            declined.update(_CLARIFY_TITLE_RE.findall(turn.content))
    return declined


def _clarify_reply(titles: list[str], want_cyrillic: bool) -> str:
    """Aniqlashtiruvchi savol matni. Mahsulot NOMI lotincha qoladi (katalog
    ro'yxatidagi kabi) — faqat atrofidagi matn kirillga o'giriladi."""

    def t(text: str) -> str:
        return to_cyrillic(text) if want_cyrillic else text

    if len(titles) == 1:
        return (
            f"{t(_CLARIFY_MARKER)}: "
            + t("Turonbankning ")
            + f"«{titles[0]}» "
            + t(
                "mahsuloti haqida so'rayapsizmi? Shunday bo'lsa \"ha\" deb yozing. "
                "Umumiy tushuncha haqida bo'lsa, savolingizni to'liqroq yozing."
            )
        )
    numbered = "\n".join(f"{i}. «{title}»" for i, title in enumerate(titles, 1))
    return (
        f"{t(_CLARIFY_MARKER)}, "
        + t("qaysi biri haqida so'rayapsiz?")
        + f"\n{numbered}\n"
        + t(
            "Raqamini yoki nomini yozing. Umumiy tushuncha haqida bo'lsa, "
            "savolingizni to'liqroq yozing."
        )
    )


def _resolve_clarification(
    question: str, history: list[ChatTurn] | None
) -> str | None:
    """Aniqlashtiruvchi savolimizga berilgan javobni mahsulot NOMIga aylantiradi.

    Shu tufayli foydalanuvchi "ha" deb yozganda bot salomlashib ketmaydi
    (router "ha" ni o'zicha salomlashish deb biladi), balki o'sha mahsulot
    haqida javob beradi.
    """
    if not history:
        return None
    last = next((t for t in reversed(history) if t.role == "assistant"), None)
    if last is None:
        return None
    content_latin = to_latin(last.content)
    if _CLARIFY_MARKER.lower() not in content_latin.lower():
        return None
    titles = _CLARIFY_TITLE_RE.findall(last.content)
    if not titles or len(titles) > _CLARIFY_MAX_OPTIONS:
        return None

    words = _words(_norm_for_match(_norm_apostrophes(to_latin(question))))
    # Uzun javob — bu tanlov emas, yangi savol
    if not words or len(words) > 6:
        return None
    if words[0].isdigit():
        index = int(words[0])
        return titles[index - 1] if 1 <= index <= len(titles) else None
    # Nomi bilan javob bergan ("meros omonati")
    for title in titles:
        toks = [w for w in _words(_norm_for_match(to_latin(title))) if len(w) >= 3]
        if toks and all(w in words for w in toks):
            return title
    # "ha" — faqat bitta variant taklif qilingan bo'lsa tushunarli
    if len(titles) == 1 and all(w in _AFFIRMATIVE_WORDS for w in words):
        return titles[0]
    return None


def _category_from_text(title: str, text: str) -> str:
    """Havolasiz yozuv uchun turkumni sarlavha va matndan taxmin qiladi.

    Sarlavhadagi so'z MATNDAGIDAN kuchliroq: mahsulot matnida boshqa turkum
    so'zi ham uchraydi (omonat tavsifida "kredit olish imkoniyati" kabi),
    lekin nomda odatda faqat o'zining turkumi bo'ladi. Shu sabab nomdagi
    moslik 10 barobar og'irroq baholanadi."""
    title_words = _text_words(title)
    body = _norm_apostrophes(to_latin(text)).replace("'", "").lower()
    best_label, best_score = "Boshqa xizmatlar", 0
    for label, keywords in _CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            kw_flat = kw.replace("'", "")
            if any(_word_match(w, kw_flat) for w in title_words):
                score += 10
            # FILIAL faqat NOMIDAN aniqlanadi: ichki hujjat (nizom, tartib)
            # matnida "bank xizmatlari markazi" ko'p uchraydi va u filiallar
            # ro'yxatiga tushib qolardi ("...mukofotlash Tartibi", 2026-11-12).
            if label != _BRANCH_LABEL:
                score += body.count(kw_flat)
        if score > best_score:
            best_label, best_score = label, score
    return best_label if best_score else "Boshqa xizmatlar"


def _word_match(a: str, b: str) -> bool:
    """Ikki so'z o'zbekcha qo'shimcha farqi bilan bir xilmi: "bank" ~
    "banklari", "avtokreditlar" ~ "avtokrediti", "tashkil" ~ "tashkil".

    Bu yerda _prefix_match ISHLATILMAYDI: u umumiy prefiks qisqa so'zning
    60% ini qamrasa yetarli deb biladi va "MIKROqarz" bilan "MIKROkrediti"
    ni bir xil deb topardi — natijada "mikroqarz turlari" so'roviga
    mikrokreditlar ham qo'shilib ketardi. Bu yerda qisqa so'z deyarli TO'LIQ
    mos kelishi talab qilinadi (oxirgi bitta harf farqiga ruxsat)."""
    cp = _common_prefix_len(a, b)
    if not (cp >= 4 and cp >= min(len(a), len(b)) - 1):
        return False
    # Qolgan qism QO'SHIMCHA bo'lishi shart, yangi so'z bo'lagi emas. Aks
    # holda "KONTR kafolat" savoli "KONTRakt" so'zli ta'lim kreditini
    # topib, model "kontr kafolat"ni "kontrakt kafolati" deb talqin qildi.
    return _is_suffix_tail(a[cp:]) and _is_suffix_tail(b[cp:])


# So'z oxiridagi qo'shimchalar (o'zbek + eng ko'p ruscha kelishik oxirlari,
# lotinga o'girilgan holda). Qisqa qoldiq (<=2 harf) har doim ruxsat —
# "krediti", "kredita", "kreditov" kabi.
_WORD_SUFFIXES = (
    "lar", "ning", "dan", "dagi", "gacha", "imiz", "ingiz", "lik", "chi",
    "siz", "roq", "ish", "lash", "gan",
    "nyy", "noy", "nogo", "nym", "nykh", "ami", "akh", "ymi",
)


def _is_suffix_tail(rest: str) -> bool:
    return len(rest) <= 2 or rest.startswith(_WORD_SUFFIXES)


def _text_words(text: str) -> set[str]:
    """Matnni solishtirishga tayyor so'zlarga ajratadi (lotin, apostrofsiz)."""
    return set(_words(_norm_apostrophes(to_latin(text)).replace("'", "")))


def _title_has(title: str, word: str) -> bool:
    """Mahsulot NOMIda shu so'z bormi."""
    return any(_word_match(t, word) for t in _text_words(title))


# Foydalanuvchi valyutani kod bilan ham, nomi bilan ham so'raydi ("dollar",
# "yevro", "funt"). Kod bo'yicha filtrlash uchun shu ro'yxat.
_CURRENCY_ALIASES: dict[str, tuple[str, ...]] = {
    "USD": ("usd", "dollar"),
    "EUR": ("eur", "evro", "yevro", "euro"),
    "GBP": ("gbp", "funt", "sterling"),
    "JPY": ("jpy", "iyena", "iena", "yena"),
    "CHF": ("chf", "frank"),
    "RUB": ("rub", "rubl"),
    "KZT": ("kzt", "tenge", "tenga"),
}

# Kanal (tab) — savolda qaysi so'z uchrasa o'sha kanal so'ralgan hisoblanadi.
_RATE_CHANNEL_HINTS: dict[str, tuple[str, ...]] = {
    "tab1": ("shoxobcha", "shahobcha", "shoxabcha", "ayirboshlash", "ofisda"),
    "tab2": ("ilova", "myturon", "my turon", "mobil"),
    "tab3": ("bankomat", "atm"),
}


# So'm yozilishlari (apostroflar _norm_apostrophes bilan bir xillashtirilgan),
# qo'shimchalari bilan: "so'mga", "somda". To'liq moslik — "summa" so'm emas.
_SOM_UNIT_RE = re.compile(r"(so'm|som|sum|uzs|сум|сўм)(ga|da|ni|dan|lik)?")
# Summa: "120", "1 000 000", "12 023.46", ixtiyoriy "ming"/"mln" va birlik.
# Birlik raqamga yopishib ham yozilishi mumkin ("120dollar", "120$").
_AMOUNT_RE = re.compile(
    r"(?<![\d.,])(\d{1,3}(?:[  ]\d{3})+|\d+)(?:[.,](\d+))?\s*"
    r"(ming|mln|million|mlrd|milliard)?\s*(\$|[a-z'а-яёўқғҳ]+)?(?:\s+([a-z'а-яёўқғҳ]+))?"
)


def _amount_unit(word: str | None) -> str | None:
    """Birlik so'zidan valyuta kodi: "dollari" -> "USD", "so'mga" -> "UZS"."""
    if not word:
        return None
    if word == "$":
        return "USD"
    if _SOM_UNIT_RE.fullmatch(word):
        return "UZS"
    for code, aliases in _CURRENCY_ALIASES.items():
        if any(word.startswith(a) for a in aliases):
            return code
    return None
_AMOUNT_MULT = {
    "ming": 1_000,
    "mln": 1_000_000,
    "million": 1_000_000,
    "mlrd": 1_000_000_000,
    "milliard": 1_000_000_000,
}
# Javobdagi raqamni solishtirish uchun ajratish ("11 970", "12 023,46", "120")
_NUMBER_RE = re.compile(r"\d{1,3}(?:[  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?")


def _fmt_amount(x: float, decimals: int) -> str:
    """1436400 -> "1 436 400"; 1442815.2 (2 xona) -> "1 442 815.20"."""
    return f"{x:,.{decimals}f}".replace(",", " ")


def _numbers_in(text: str) -> set[float]:
    """Matndagi barcha sonlar (bo'shliqli minglar va vergulli kasr bilan)."""
    out: set[float] = set()
    for m in _NUMBER_RE.findall(text):
        try:
            out.add(round(float(m.replace(" ", "").replace(" ", "").replace(",", ".")), 2))
        except ValueError:
            continue
    return out


def _parse_amounts(q: str) -> list[tuple[float, str]]:
    """Savoldagi summalar: [(miqdor, valyuta_kodi yoki "UZS")].

    Faqat birligi aniq yozilgan summa olinadi ("120 dollar", "$120",
    "1 mln so'm") — birliksiz son (sana, karta raqami) hisobga kirmaydi."""
    found: list[tuple[float, str]] = []
    for m in re.finditer(r"\$\s*(\d+(?:[.,]\d+)?)", q):
        found.append((float(m.group(1).replace(",", ".")), "USD"))
    for m in _AMOUNT_RE.finditer(q):
        whole, frac, mult, unit, unit2 = m.groups()
        # Birlik keyingi so'zda ham bo'lishi mumkin: "120 AQSh dollari"
        code = _amount_unit(unit) or _amount_unit(unit2)
        if not code:
            continue
        value = float(whole.replace(" ", "").replace(" ", "") + (f".{frac}" if frac else ""))
        value *= _AMOUNT_MULT.get(mult or "", 1)
        if value > 0 and (value, code) not in found:
            found.append((value, code))
    return found


def _rates_calculation(
    q: str, data: dict[str, Any], wanted_codes: set[str], wanted_channels: set[str]
) -> str:
    """Savolda summa bo'lsa — konvertatsiyani KOD hisoblaydi (model emas).

    Valyuta -> so'm: bank valyutani SOTIB OLISH kursi bo'yicha;
    so'm -> valyuta: bank valyutani SOTISH kursi bo'yicha. Har birida
    Markaziy bank kursi bo'yicha natija ham beriladi (taqqoslash uchun).
    Kanal aytilmagan bo'lsa — birinchi kanal (ayirboshlash shoxobchasi)."""
    amounts = _parse_amounts(q)
    if not amounts:
        return ""
    channels = data.get("channels") or []
    channel = next(
        (c for c in channels if c.get("key") in wanted_channels), channels[0] if channels else None
    )
    if not channel:
        return ""
    rows = {str(r.get("code")): r for r in channel.get("rows", [])}

    lines: list[str] = []
    for value, code in amounts:
        if code == "UZS":
            # So'mdan valyutaga: valyuta aytilmagan bo'lsa — USD
            for target in sorted(wanted_codes) or ["USD"]:
                row = rows.get(target)
                if not row:
                    continue
                if row.get("sell"):
                    lines.append(
                        f"{_fmt_amount(value, 0)} so'mga bankdan {target} sotib olsangiz "
                        f"(sotish kursi {_fmt_amount(float(row['sell']), 2 if float(row['sell']) % 1 else 0)}): "
                        f"{_fmt_amount(value / float(row['sell']), 2)} {target}"
                    )
                if row.get("cb"):
                    lines.append(
                        f"Markaziy bank kursi ({_fmt_amount(float(row['cb']), 2)}) bo'yicha: "
                        f"{_fmt_amount(value / float(row['cb']), 2)} {target}"
                    )
            continue
        row = rows.get(code)
        if not row:
            continue
        shown = _fmt_amount(value, 2 if value % 1 else 0)
        if row.get("buy"):
            buy = float(row["buy"])
            lines.append(
                f"{shown} {code} ni bankka sotsangiz (sotib olish kursi "
                f"{_fmt_amount(buy, 2 if buy % 1 else 0)}): {_fmt_amount(value * buy, 0)} so'm"
            )
        if row.get("cb"):
            cb = float(row["cb"])
            lines.append(
                f"Markaziy bank kursi ({_fmt_amount(cb, 2)}) bo'yicha: "
                f"{_fmt_amount(value * cb, 2)} so'm"
            )
    if not lines:
        return ""
    return f"Hisob ({channel['label']} kursi bo'yicha):\n" + "\n".join(f"* {ln}" for ln in lines)


def _rates_to_cyrillic(text: str) -> str:
    """Kurs javobini kirillga o'giradi, lekin valyuta KODLARI (USD, EUR...),
    havola va ilova nomi lotincha qoladi — "УСД" deb yozish xato bo'lardi."""
    keep = list(_CURRENCY_ALIASES) + ["MyTuron", RATES_URL]
    return _translit_preserving_titles(text, keep)


def _format_history(
    history: list[ChatTurn] | None,
    limit: int,
    msg_chars: int,
    total_chars: int,
) -> str:
    """Suhbat tarixini promptga sig'adigan qilib tayyorlaydi.

    Uzun xabar (masalan 20 bandli mahsulot ro'yxati) qisqartiriladi va umumiy
    hajm ham cheklanadi — aks holda ikkita shunday javob promptning yarmini
    egallab, prompt num_ctx dan oshib ketardi va model javob bermay qolardi.
    Eng OXIRGI xabarlar muhimroq, shuning uchun oxiridan boshlab yig'amiz."""
    if not history:
        return ""
    lines: list[str] = []
    used = 0
    for turn in reversed(history[-limit:]):
        text = " ".join(turn.content.split())
        if len(text) > msg_chars:
            text = text[:msg_chars].rstrip() + "..."
        line = f"{'User' if turn.role == 'user' else 'Assistant'}: {text}"
        if lines and used + len(line) > total_chars:
            break
        lines.append(line)
        used += len(line)
    return "\n".join(reversed(lines))


def _is_ru_doc(payload: dict[str, Any]) -> bool:
    """Bilim bazasidagi bo'lak ruscha hujjatdanmi. `lang` maydoni yo'q eski
    yozuvlar o'zbekcha hisoblanadi."""
    return payload.get("lang") == "ru"


def _merge_results(
    primary: list[tuple[dict[str, Any], float]],
    extra: list[tuple[dict[str, Any], float]],
) -> list[tuple[dict[str, Any], float]]:
    """Vektor va leksik natijalarni NAVBAT bilan birlashtiradi:
    vektor[0], leksik[0], vektor[1], leksik[1], ...

    Navbatlashtirish shart. Promptdagi kontekstga belgilar byudjeti bor va
    ro'yxat OXIRIDAGI bo'laklar kesib tashlanadi. Leksik natijalar oxiriga
    qo'shilganda aynan o'shalar kesilardi: "qachon tashkil qilingan" savoliga
    to'g'ri bo'lak TOPILGAN bo'lsa ham promptga tushmay qolardi va model
    yana "ma'lumot yo'q" derdi."""

    def key(p: dict[str, Any]) -> tuple[str, Any]:
        return str(p.get("title", "")), p.get("chunk_index")

    out: list[tuple[dict[str, Any], float]] = []
    seen: set[tuple[str, Any]] = set()
    for pair in chain.from_iterable(zip_longest(primary, extra)):
        if pair is None:
            continue
        payload, score = pair
        if key(payload) not in seen:
            seen.add(key(payload))
            out.append((payload, score))
    return out


def _narrow_by_title(
    words: list[str], items: list[tuple[str, str]]
) -> list[tuple[str, str]] | None:
    """Turkumni savoldagi qo'shimcha so'zlar bo'yicha MAHSULOT NOMLARI orqali
    toraytiradi.

    Nomlar bo'yicha ishlanadi, mahsulot MATNI bo'yicha emas: matnda "ipoteka"
    so'zi boshqa kredit tavsifida ham uchrab, ro'yxatni buzardi. Nom esa qisqa
    va bankda izchil yozilgan ("... Avtokrediti", "Ipoteka krediti ...").

    None qaytsa — bu so'zlar nomlarni ajratmaydi (mahsulot xususiyati haqidagi
    savol); chaqiruvchi bunday savolni modelga beradi."""
    picked = list(items)
    narrowed = False
    for w in words:
        hits = [(t, x) for t, x in picked if _title_has(t, w)]
        if len(hits) == len(picked):
            continue  # hech narsani ajratmaydi — e'tiborsiz qoldiramiz
        if not hits:
            return None  # bunday nomdagi mahsulot yo'q
        picked, narrowed = hits, True
    return picked if narrowed else None
