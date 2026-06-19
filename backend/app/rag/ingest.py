"""
PDF'larni Qdrant vector bazasiga yozish (BIR MARTALIK terminal skripti).

Oqim:  PDF -> matn (ocr) -> bo'laklar (chunking) -> vektor (embeddings)
       -> Qdrant ga saqlash (vektor + matn + manba)

Bu VEB-SO'ROV EMAS! Shuning uchun 2 soat ketsa ham timeout bo'lmaydi.

Docker ichida ishga tushirish (tesseract avtomatik bor):
    docker compose run --rm backend python -m app.rag.ingest
"""
from pathlib import Path
from qdrant_client.models import PointStruct

from app.rag.ocr import pdf_dan_sahifalar
from app.rag.chunking import boluklarga_bol, sarlavha_aniqla
from app.rag.embeddings import vektorla
from app.rag.db import client, COLLECTION, collection_tayyorla

HUJJATLAR = Path("data/documents")


def yukla():
    collection_tayyorla()

    pdf_lar = sorted(HUJJATLAR.glob("*.pdf"))
    if not pdf_lar:
        print("data/documents/ ichida PDF topilmadi.")
        return

    print(f"{len(pdf_lar)} ta PDF topildi\n")
    keyingi_id = 0

    for pdf in pdf_lar:
        print(f">>> {pdf.name}")
        sahifalar = pdf_dan_sahifalar(str(pdf))
        matn = "\n".join(sahifalar)
        boluklar = boluklarga_bol(matn)
        if not boluklar:
            print("  (matn topilmadi, o'tkazib yuborildi)\n")
            continue

        # 1-betdan hujjat mavzusini (sarlavhasini) avtomatik olamiz
        sarlavha = sarlavha_aniqla(sahifalar[0]) if sahifalar else pdf.stem
        print(f"  sarlavha: {sarlavha[:90]}...")

        # Embedding qilishda sarlavhani har bo'lak oldiga qo'shamiz -- shunda
        # qidiruv "bu bo'lak qaysi hujjatdan" ekanini hisobga oladi.
        vektor_matnlar = [f"[{sarlavha}]\n{b}" for b in boluklar]
        vektorlar = vektorla(vektor_matnlar)
        nuqtalar = []
        for i, (bolak, vektor) in enumerate(zip(boluklar, vektorlar)):
            nuqtalar.append(
                PointStruct(
                    id=keyingi_id,
                    vector=vektor,
                    payload={
                        "matn": bolak,
                        "sarlavha": sarlavha,
                        "manba": pdf.name,
                        "bolak": i,
                    },
                )
            )
            keyingi_id += 1

        client.upsert(collection_name=COLLECTION, points=nuqtalar)
        print(f"  {len(nuqtalar)} bo'lak bazaga yozildi\n")

    jami = client.count(collection_name=COLLECTION).count
    print(f"===== JAMI BAZADA: {jami} bo'lak =====")


if __name__ == "__main__":
    yukla()
