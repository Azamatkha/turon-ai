"""Turonbank valyuta kurslari sahifasini toza matnga aylantiradi.

Sahifada 3 ta jadval (tab) bor: ayirboshlash shoxobchasida / ilovada /
bankomatda. Har birida ustunlar: Valyuta (kod + nom), Sotib olish, Sotish,
MB kursi.

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

# tab kodi -> ko'rsatiladigan nom
_TAB_NAMES = {
    "tab1": "Ayirboshlash shoxobchasida",
    "tab2": "Ilovada",
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


def parse_rates(html: str) -> str:
    """Sahifa HTML'idan kurslarni o'qib, RAG uchun toza matn qaytaradi.
    Topilmasa bo'sh satr (sahifa tuzilishi o'zgargan bo'lishi mumkin)."""
    soup = BeautifulSoup(html, "html.parser")
    blocks: list[str] = []

    for group in soup.select("div.exchange__group"):
        tab = str(group.get("data-tabs-target", ""))
        label = _TAB_NAMES.get(tab, tab or "Kurslar")
        table = group.select_one("table.exchange__table")
        if table is None:
            continue

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
                f"{code} ({name}): sotib olish {buy}, sotish {sell}, "
                f"Markaziy bank kursi {cb}."
            )

        if lines:
            blocks.append(f"{label}:\n" + "\n".join(lines))

    if not blocks:
        return ""

    # "16.07.2026 09:00:00 dan ma'lumotlar" — yangilanish sanasi
    stamp = soup.find(string=_STAMP_RE)
    if stamp:
        blocks.append(_clean(str(stamp)))

    return "\n\n".join(blocks)
