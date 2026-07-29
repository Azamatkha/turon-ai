"""Turonbank valyuta kurslari sahifasini toza matnga aylantiradi.

Sahifada 3 ta jadval (tab) bor: ayirboshlash shoxobchasida / ilovada /
bankomatda. Har birida ustunlar: Valyuta (kod + nom), Sotib olish, Sotish,
MB kursi. UCHALASI ham o'qiladi — foydalanuvchi "bankomatda qancha" yoki
"MyTuronda qancha" deb so'rashi mumkin.

Kurslar HTML'ning o'zida (server tomonda) render qilinadi — JS kerak emas,
oddiy HTTP fetch yetarli.

HTML tuzilishi:
    div.exchange__group[data-tabs-target="tab1"]
      table.exchange__table
        tr > td > div.currency-name > .currency-name__code / .currency-name__text
        tr > td > div.exchange-value > span
"""

import re
from typing import Any

from bs4 import BeautifulSoup

RATES_URL = "https://turonbank.uz/uz/services/exchange-rates/"
# Vektor bazadagi sarlavha — har kuni shu sarlavha ostidagi eski yozuv
# o'chirilib, yangisi yoziladi.
RATES_TITLE = "Valyuta kurslari"

# tab kodi -> ko'rsatiladigan nom. tab2 uchun ilova nomi ham yozilgan —
# foydalanuvchilar uni "MyTuron" deb so'raydi, "ilovada" degan so'z bilan
# qidiruvda mos kelmasdi.
_TAB_NAMES = {
    "tab1": "Ayirboshlash shoxobchasida",
    "tab2": "Ilovada (MyTuron mobil ilovasida)",
    "tab3": "Bankomatda",
}

_STAMP_RE = re.compile(r"dan\s+ma.?lumotlar")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _cell_value(td: Any) -> str:
    """Katakdagi raqamni oladi (div.exchange-value > span)."""
    holder = td.select_one(".exchange-value") or td
    span = holder.find("span")
    return _clean((span or holder).get_text(" ", strip=True))


def _table_lines(group: Any) -> list[str]:
    """Bitta tab jadvalidagi valyuta qatorlarini matn qilib qaytaradi."""
    table = group.select_one("table.exchange__table")
    if table is None:
        return []

    lines: list[str] = []
    for tr in table.find_all("tr"):
        if tr.find("th"):
            continue  # sarlavha qatori
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 4:
            continue
        code_el = tds[0].select_one(".currency-name__code")
        name_el = tds[0].select_one(".currency-name__text")
        code = _clean(code_el.get_text()) if code_el else ""
        name = _clean(name_el.get_text()) if name_el else ""
        if not code and not name:
            continue
        buy = _cell_value(tds[1])
        sell = _cell_value(tds[2])
        cb = _cell_value(tds[3])
        lines.append(
            f"{code} ({name}): sotib olish {buy} so'm, sotish {sell} so'm, "
            f"Markaziy bank kursi {cb} so'm."
        )
    return lines


def _stamp_text(soup: BeautifulSoup) -> str:
    """"16.07.2026 09:00:00 dan ma'lumotlar" — kurs qaysi vaqtga tegishli."""
    stamp = soup.find(string=_STAMP_RE)
    return _clean(str(stamp)) if stamp else ""


def parse_rates(html: str) -> str:
    """Sahifadagi UCHALA kurs jadvalini (ayirboshlash shoxobchasi / ilova /
    bankomat) toza matn qilib qaytaradi. Topilmasa bo'sh satr.

    IKKI MUHIM JIHAT:
      * Ilgari faqat tab1 (shoxobcha) olinardi — shuning uchun "bankomatda
        qancha" degan savolga javob yo'q edi. Endi har uchala kanal ham bor.
      * Yangilanish sanasi ilgari matn OXIRIGA alohida blok qilib qo'yilardi;
        matn chunk'larga bo'linganda sana kurslardan ajralib qolib, model
        javobda sanani ko'rsata olmasdi. Endi sana HAR BIR blokning birinchi
        qatorida turadi — qaysi bo'lak topilsa ham sana u bilan birga keladi.
    """
    soup = BeautifulSoup(html, "html.parser")
    groups = soup.select("div.exchange__group")
    if not groups:
        return ""

    stamp = _stamp_text(soup)
    # Har blokda takrorlanadi — chunk'ga bo'linganda ham sana yo'qolmasin.
    as_of = f" — {stamp}" if stamp else ""

    blocks: list[str] = []
    for group in groups:
        tab = str(group.get("data-tabs-target", ""))
        label = _TAB_NAMES.get(tab)
        if label is None:
            continue
        lines = _table_lines(group)
        if not lines:
            continue
        blocks.append(
            f"Turonbank valyuta kurslari — {label}{as_of}:\n" + "\n".join(lines)
        )

    return "\n\n".join(blocks)
