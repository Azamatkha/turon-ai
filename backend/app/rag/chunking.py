"""
2-QADAM: Uzun matnni kichik "bo'lak"larga bo'lish.

Nega? 2000 so'zlik hujjatni butunligicha bazaga/AI'ga berib bo'lmaydi.
Uni ~800 belgilik bo'laklarga bo'lamiz.

MUHIM: bo'laklar GAP va SO'Z chegarasini hurmat qiladi -- so'z yoki gap
o'rtasidan kesilmaydi. Bo'laklar biroz USTMA-UST tushadi (oldingi bo'lakning
oxirgi bir necha so'zi keyingisiga qo'shiladi), shunda kontekst yo'qolmaydi.
"""
import re


def boluklarga_bol(matn: str, bolak_olchami: int = 800, ustma_ust: int = 150):
    """Matnni gaplar bo'yicha to'plab, ~bolak_olchami belgili bo'laklar qiladi."""
    matn = " ".join(matn.split())          # ortiqcha bo'sh joy/qatorni tozalaymiz
    if not matn:
        return []

    # Matnni gaplarga ajratamiz (. ! ? belgilaridan keyin)
    gaplar = re.split(r"(?<=[.!?])\s+", matn)

    boluklar = []
    joriy = ""
    for gap in gaplar:
        # Gap juda uzun bo'lsa (masalan uzun ro'yxat) -> so'z bo'yicha bo'lamiz
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

        # Oddiy hol: gap joriy bo'lakka sig'sa qo'shamiz, sig'masa yangisini boshlaymiz
        if len(joriy) + len(gap) + 1 > bolak_olchami:
            boluklar.append(joriy)
            joriy = gap
        else:
            joriy = (joriy + " " + gap).strip()

    if joriy:
        boluklar.append(joriy)

    # USTMA-UST: har bo'lak boshiga oldingi bo'lakning oxirgi so'zlarini qo'shamiz
    # (so'z o'rtasidan boshlanmasligi uchun butun so'zlarni olamiz)
    if ustma_ust > 0 and len(boluklar) > 1:
        natija = [boluklar[0]]
        for i in range(1, len(boluklar)):
            oldingi = boluklar[i - 1]
            dum = oldingi[-ustma_ust:]
            dum = dum.split(" ", 1)[1] if " " in dum else dum   # yarim so'zni tashlaymiz
            natija.append((dum + " " + boluklar[i]).strip())
        boluklar = natija

    return [b for b in boluklar if b]


# Hujjat turini bildiruvchi kalit so'zlar (sarlavhada shulardan biri bo'ladi)
HUJJAT_TURLARI = [
    "nizom", "qaror", "yo'riqnoma", "yo`riqnoma", "yoriqnoma", "ruhsatnoma",
    "tartib", "reglament", "siyosat", "strategiya", "qoida",
]


def sarlavha_aniqla(birinchi_sahifa: str, maks: int = 200) -> str:
    """
    PDF'ning 1-betidan hujjat MAVZUSINI (sarlavhasini) avtomatik ajratadi.
    Aniq sarlavha topilmasa -> 1-betning boshidagi mazmunli matnni qaytaradi.
    """
    matn = " ".join(birinchi_sahifa.split())
    if not matn:
        return ""

    past = matn.lower()
    # Hujjat turi so'zini topib (eng birinchisini), uning ATROFIDAGI matnni olamiz
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

    # Topilmasa: 1-betning birinchi mazmunli qismi
    return matn[:maks].strip()


if __name__ == "__main__":
    namuna = ("Bank ichki qoida. \"Falonchi\" bankning ichki nazorat "
              "tartibi to'g'risida Nizom. " + "Bu test matni. " * 200)
    natija = boluklarga_bol(namuna)
    print(f"{len(natija)} ta bo'lak hosil bo'ldi")
    print("Birinchi bo'lak:", natija[0][:120], "...")
    print("\nSarlavha:", sarlavha_aniqla(namuna))
