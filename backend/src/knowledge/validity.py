"""Bilim bazasi hujjatlarining amal qilish muddati (`valid_until`).

Muddat sarlavha darajasida: bir sarlavhaning barcha bo'laklari payload'ida
bir xil `valid_until` ("YYYY-MM-DD") turadi. Muddat o'tgan hujjat
o'chirilmaydi — u qidiruvda pastroq turadi va model javobda "ma'lumot
eskirgan bo'lishi mumkin" deb ogohlantiradi; adminga esa bildirishnoma boradi.
"""

from datetime import date, timedelta
from typing import Any

from src.core.utils.datetime_utils import get_utc_now

# Muddati o'tgan hujjat balli shunga ko'paytiriladi: butunlay yo'qolmaydi
# (boshqa manba bo'lmasa baribir javob beradi), lekin yangi hujjat bo'lsa
# u oldinga chiqadi.
EXPIRED_PENALTY = 0.85
# Adminga "muddati yaqinlashmoqda" xabari shuncha kun oldin boradi
WARN_DAYS = 7


def today() -> date:
    # Toshkent = UTC+5: bank kuni UTC'dan oldin boshlanadi
    return (get_utc_now() + timedelta(hours=5)).date()


def parse_valid_until(payload: dict[str, Any]) -> date | None:
    raw = payload.get("valid_until")
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def is_expired(payload: dict[str, Any], on: date | None = None) -> bool:
    vu = parse_valid_until(payload)
    return vu is not None and vu < (on or today())


def penalize_expired(
    results: list[tuple[dict[str, Any], float]],
) -> list[tuple[dict[str, Any], float]]:
    """Muddati o'tgan bo'laklarning ballini pasaytirib, qayta saralaydi."""
    if not any(is_expired(p) for p, _ in results):
        return results
    rescored = [(p, s * EXPIRED_PENALTY if is_expired(p) else s) for p, s in results]
    rescored.sort(key=lambda pair: -pair[1])
    return rescored


def expiry_events(
    payloads: list[dict[str, Any]], on: date | None = None
) -> tuple[list[str], list[str]]:
    """(muddati WARN_DAYS kundan keyin tugaydiganlar, bugun tugaganlar).

    Faqat aniq shu ikki kunda — har kuni bir xil xabar yuborilmasin.
    """
    d = on or today()
    soon_day = d + timedelta(days=WARN_DAYS)
    soon: dict[str, None] = {}
    expired: dict[str, None] = {}
    for p in payloads:
        vu = parse_valid_until(p)
        title = str(p.get("title", ""))
        if vu is None or not title:
            continue
        if vu == soon_day:
            soon[title] = None
        elif vu == d - timedelta(days=1):
            # valid_until — oxirgi amal qiladigan kun; ertasi kuni "tugadi"
            expired[title] = None
    return list(soon), list(expired)
