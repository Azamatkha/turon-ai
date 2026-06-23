"""
PDF'larni Qdrant vektor bazasiga yozish (BIR MARTALIK terminal skripti).

Oqim:  PDF -> matn (ocr) -> bo'laklar (chunking) -> vektor (embeddings)
       -> Qdrant ga saqlash (vektor + matn + manba)

Bu VEB-SO'ROV EMAS! Shuning uchun 2 soat ketsa ham timeout bo'lmaydi.

Docker ichida ishga tushirish:
    docker compose run --rm app python -m src.rag.ingest
"""
from pathlib import Path

from qdrant_client.models import PointStruct

from src.rag.chunking import boluklarga_bol, sarlavha_aniqla
from src.rag.embeddings import vektorla
from src.rag.ocr import pdf_dan_sahifalar
from src.rag.qdrant_client import COLLECTION, client, collection_tayyorla

HUJJATLAR = Path("data/documents")


def yukla() -> int:
    """Barcha PDF'ni o'qib bazaga yozadi. Bazadagi jami bo'lak sonini qaytaradi."""
    collection_tayyorla()

    pdf_lar = sorted(HUJJATLAR.glob("*.pdf"))
    if not pdf_lar:
        print("data/documents/ ichida PDF topilmadi.")
        return 0

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

        sarlavha = sarlavha_aniqla(sahifalar[0]) if sahifalar else pdf.stem
        print(f"  sarlavha: {sarlavha[:90]}...")

        # Sarlavhani har bo'lak oldiga qo'shamiz -> qidiruv "qaysi hujjat"ni biladi.
        vektor_matnlar = [f"[{sarlavha}]\n{b}" for b in boluklar]
        vektorlar = vektorla(vektor_matnlar)
        nuqtalar = [
            PointStruct(
                id=keyingi_id + i,
                vector=vektor,
                payload={"matn": bolak, "sarlavha": sarlavha, "manba": pdf.name, "bolak": i},
            )
            for i, (bolak, vektor) in enumerate(zip(boluklar, vektorlar))
        ]
        keyingi_id += len(nuqtalar)

        client.upsert(collection_name=COLLECTION, points=nuqtalar)
        print(f"  {len(nuqtalar)} bo'lak bazaga yozildi\n")

    jami = client.count(collection_name=COLLECTION).count
    print(f"===== JAMI BAZADA: {jami} bo'lak =====")
    return jami


if __name__ == "__main__":
    yukla()
