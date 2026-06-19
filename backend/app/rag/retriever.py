"""
AI'SIZ TEKSHIRUV: Qdrant'дан savolga mos bo'laklarni qidirish.

Bu hali AI emas! Faqat "vector baza to'g'ri ishlayaptimi?" tekshiruvi.

Ishga tushirish:
    docker compose run --rm backend python -m app.rag.retriever "PQ-500 qaror"
"""
from app.rag.embeddings import vektorla
from app.rag.db import client, COLLECTION


def qidir(savol: str, top_k: int = 3):
    savol_vektor = vektorla([savol])[0]
    natija = client.query_points(
        collection_name=COLLECTION,
        query=savol_vektor,
        limit=top_k,
    )
    return natija.points


if __name__ == "__main__":
    import sys
    savol = sys.argv[1] if len(sys.argv) > 1 else "PQ-500 qaror"
    print(f"Savol: {savol}\n")
    for hit in qidir(savol):
        manba = hit.payload["manba"]
        sarlavha = hit.payload.get("sarlavha", "-")
        matn = hit.payload["matn"]
        print(f"--- manba: {manba} (o'xshashlik: {hit.score:.3f}) ---")
        print(f"    mavzu: {sarlavha[:90]}")
        print(matn[:400])
        print()
