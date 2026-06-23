"""
2-QADAM: Uzun matnni kichik "bo'lak"larga bo'lish.

~800 belgilik bo'laklar, gap/so'z chegarasini hurmat qilib, 150 belgi ustma-ust
bilan (kontekst yo'qolmasligi uchun). 1-betdan hujjat sarlavhasi aniqlanadi.
"""
import re


def boluklarga_bol(matn: str, bolak_olchami: int = 800, ustma_ust: int = 150):
    """Matnni gaplar bo'yicha to'plab, ~bolak_olchami belgili bo'laklar qiladi."""
    matn = " ".join(matn.split())
    if not matn:
        return []

    gaplar = re.split(r"(?<=[.!?])\s+", matn)

    boluklar = []
    joriy = ""
    for gap in gaplar:
        if len(gap) > bolak_olchami:
            if joriy:
                boluklar.append(joriy)
                joriy = ""
            for suz in gap.split(" "):
                if len(joriy) + len(suz) + 1 > bolak_olchami:
                    boluklar.append(joriy)
                    joriy = suz
                else:
                    joriy = (joriy + " " + suz).strip()
            continue

        if len(joriy) + len(gap) + 1 > bolak_olchami:
            boluklar.append(joriy)
            joriy = gap
        else:
            joriy = (joriy + " " + gap).strip()

    if joriy:
        boluklar.append(joriy)

    # USTMA-UST: har bo'lak boshiga oldingi bo'lakning oxirgi so'zlarini qo'shamiz
    if ustma_ust > 0 and len(boluklar) > 1:
        natija = [boluklar[0]]
        for i in range(1, len(boluklar)):
            dum = boluklar[i - 1][-ustma_ust:]
            dum = dum.split(" ", 1)[1] if " " in dum else dum
            natija.append((dum + " " + boluklar[i]).strip())
        boluklar = natija

    return [b for b in boluklar if b]


HUJJAT_TURLARI = [
    "nizom", "qaror", "yo'riqnoma", "yo`riqnoma", "yoriqnoma", "ruhsatnoma",
    "tartib", "reglament", "siyosat", "strategiya", "qoida",
]


def sarlavha_aniqla(birinchi_sahifa: str, maks: int = 200) -> str:
    """1-betdan hujjat MAVZUSINI (sarlavhasini) ajratadi; topilmasa bosh qismini."""
    matn = " ".join(birinchi_sahifa.split())
    if not matn:
        return ""

    past = matn.lower()
    eng_yaqin = None
    topilgan = ""
    for tur in HUJJAT_TURLARI:
        idx = past.find(tur)
        if idx != -1 and (eng_yaqin is None or idx < eng_yaqin):
            eng_yaqin = idx
            topilgan = tur
    if eng_yaqin is not None:
        bosh = max(0, eng_yaqin - 120)
        oxir = min(len(matn), eng_yaqin + len(topilgan) + 30)
        return matn[bosh:oxir].strip()

    return matn[:maks].strip()
