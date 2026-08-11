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


def _to_number(raw: str) -> float | None:
    """Katakdagi matnni songa aylantiradi. Saytda raqam bo'sh joy bilan
    ajratilgan bo'lishi mumkin ("11 850"), kasr esa vergul yoki nuqta bilan."""
    cleaned = re.sub(r"[^\d,.\-]", "", raw).replace(",", ".")
    # Ming ajratgichi sifatida qo'yilgan ortiqcha nuqtalar ("11.850.00")
    if cleaned.count(".") > 1:
        head, _, tail = cleaned.rpartition(".")
        cleaned = head.replace(".", "") + "." + tail
    try:
        return float(cleaned)
    except ValueError:
        return None


def _table_rows(group: Any) -> list[dict[str, Any]]:
    """Bitta tab jadvalini STRUKTURALI ko'rinishda qaytaradi.

    Matn (_channel_lines) ham shu strukturadan quriladi — shunda vektor
    bazadagi matn va API qaytaradigan JSON hech qachon bir-biridan farq
    qilmaydi."""
    table = group.select_one("table.exchange__table")
    if table is None:
        return []

    rows: list[dict[str, Any]] = []
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
        # Bo'sh katak bo'lishi MUMKIN: ilova va bankomat jadvallarida ba'zi
        # valyutalar bo'yicha sotish kursi ko'rsatilmaydi — bunday maydon
        # None bo'lib qoladi va matnga umuman yozilmaydi (aks holda model
        # bo'sh joyni boshqa kanalning raqami bilan to'ldirib yuborardi).
        row = {
            "code": code,
            "name": name,
            "buy": _to_number(_cell_value(tds[1])),
            "sell": _to_number(_cell_value(tds[2])),
            "cb": _to_number(_cell_value(tds[3])),
        }
        if row["buy"] is None and row["sell"] is None and row["cb"] is None:
            continue
        rows.append(row)
    return rows


def format_amount(value: float) -> str:
    """11850.0 -> "11 850", 11934.61 -> "11 934.61" (mingliklar ajratilgan)."""
    whole = int(abs(value))
    frac = round(abs(value) - whole, 2)
    text = f"{whole:,}".replace(",", " ")
    if frac:
        text += f"{frac:.2f}".lstrip("0")
    return ("-" if value < 0 else "") + text


_FIELD_LABELS = (
    ("buy", "sotib olish"),
    ("sell", "sotish"),
    ("cb", "Markaziy bank kursi"),
)


def channel_lines(rows: list[dict[str, Any]]) -> list[str]:
    """Strukturali qatorlarni matn satrlariga aylantiradi. `delta_*` maydoni
    bo'lsa — o'zgarish qavs ichida qo'shiladi ("(+50 so'm)"), shunda chatda
    kurs so'ralganda ham o'sgan/tushganini ko'rish mumkin."""
    lines: list[str] = []
    for row in rows:
        parts: list[str] = []
        for key, label in _FIELD_LABELS:
            value = row.get(key)
            if value is None:
                continue
            piece = f"{label}: {format_amount(float(value))} so'm"
            delta = row.get(f"delta_{key}")
            if delta:
                sign = "+" if delta > 0 else ""
                shift = f"{sign}{format_amount(float(delta))}"
                piece += f" (kechagiga nisbatan {shift} so'm)"
            parts.append(piece)
        if not parts:
            continue
        lines.append(f"{row['code']} ({row['name']}): " + ", ".join(parts) + ".")
    return lines


def _stamp_text(soup: BeautifulSoup) -> str:
    """"16.07.2026 09:00:00 dan ma'lumotlar" — kurs qaysi vaqtga tegishli."""
    stamp = soup.find(string=_STAMP_RE)
    return _clean(str(stamp)) if stamp else ""


def parse_rates(html: str) -> str:
    """Sahifadagi UCHALA kurs jadvalini (ayirboshlash shoxobchasi / ilova /
    bankomat) toza matn qilib qaytaradi. Topilmasa bo'sh satr.

    Qulaylik uchun qisqartma: parse_rates_structured + render_rates. Kurs
    vazifasi ikkalasini ALOHIDA chaqiradi, chunki orasida farq (delta)
    hisoblanadi."""
    return render_rates(parse_rates_structured(html))


def parse_rates_structured(html: str) -> dict[str, Any]:
    """Sahifani STRUKTURALI ko'rinishga aylantiradi:

        {"stamp": "11.08.2026 11:10:00 dan ma'lumotlar",
         "channels": [{"key": "tab1", "label": "...", "rows": [...]}, ...]}

    Shu ko'rinish ikki joyda ishlatiladi: vektor bazaga yoziladigan matn
    (render_rates) va oynaga beriladigan JSON. Bitta manba — ikkalasi
    hech qachon bir-biriga zid bo'lmaydi."""
    soup = BeautifulSoup(html, "html.parser")
    groups = soup.select("div.exchange__group")
    if not groups:
        return {"stamp": "", "channels": []}

    channels: list[dict[str, Any]] = []
    for group in groups:
        tab = str(group.get("data-tabs-target", ""))
        label = _TAB_NAMES.get(tab)
        if label is None:
            continue
        rows = _table_rows(group)
        if not rows:
            continue
        channels.append({"key": tab, "label": label, "rows": rows})

    return {"stamp": _stamp_text(soup), "channels": channels}


def render_rates(data: dict[str, Any]) -> str:
    """Strukturali kurslarni vektor bazaga yoziladigan matnga aylantiradi.

    Sana HAR BIR blokning birinchi qatorida takrorlanadi — matn chunk'larga
    bo'linganda qaysi bo'lak topilsa ham sana u bilan birga keladi (ilgari
    sana matn oxirida yolg'iz turardi va kurslardan ajralib qolardi)."""
    stamp = str(data.get("stamp", ""))
    as_of = f" — {stamp}" if stamp else ""

    blocks: list[str] = []
    for channel in data.get("channels", []):
        lines = channel_lines(channel.get("rows", []))
        if not lines:
            continue
        blocks.append(
            f"Turonbank valyuta kurslari — {channel['label']}{as_of}:\n"
            + "\n".join(lines)
        )
    return "\n\n".join(blocks)


def apply_deltas(
    current: dict[str, Any], previous: dict[str, Any] | None
) -> dict[str, Any]:
    """Har bir valyuta uchun oldingi yangilanishga nisbatan o'zgarishni
    hisoblab, `delta_buy` / `delta_sell` / `delta_cb` maydonlarini qo'shadi.

    Oldingi ma'lumot bo'lmasa (birinchi ishga tushish yoki sana o'zgarmagan)
    delta qo'shilmaydi — noldan farqni ko'rsatish chalg'itardi."""
    if not previous or previous.get("stamp") == current.get("stamp"):
        return current

    old: dict[tuple[str, str], dict[str, Any]] = {
        (str(ch.get("key")), str(row.get("code"))): row
        for ch in previous.get("channels", [])
        for row in ch.get("rows", [])
    }
    for channel in current.get("channels", []):
        for row in channel["rows"]:
            before = old.get((str(channel.get("key")), str(row.get("code"))))
            if not before:
                continue
            for key, _ in _FIELD_LABELS:
                now, was = row.get(key), before.get(key)
                if now is None or was is None:
                    continue
                diff = round(float(now) - float(was), 2)
                if diff:
                    row[f"delta_{key}"] = diff
    return current
