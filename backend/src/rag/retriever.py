"""
Qdrant'dan savolga mos bo'laklarni qidirish (similarity search).

RAG oqimining "retrieval" qismi: savol -> vektor -> eng yaqin bo'laklar.
Topilgan bo'laklar keyin LLM'ga kontekst sifatida beriladi.

Test:
    python -m src.rag.retriever "PQ-500 qaror"
"""
from dataclasses import dataclass

from src.rag.config import RAG_TOP_K
from src.rag.embeddings import vektorla
from src.rag.qdrant_client import COLLECTION, client


@dataclass
class Bolak:
    """Qidiruvda topilgan bitta hujjat bo'lagi."""

    matn: str
    sarlavha: str
    manba: str
    score: float


def qidir(savol: str, top_k: int | None = None) -> list[Bolak]:
    top_k = top_k or RAG_TOP_K
    savol_vektor = vektorla([savol])[0]
    natija = client.query_points(
        collection_name=COLLECTION,
        query=savol_vektor,
        limit=top_k,
    )
    return [
        Bolak(
            matn=hit.payload["matn"],
            sarlavha=hit.payload.get("sarlavha", ""),
            manba=hit.payload["manba"],
            score=hit.score,
        )
        for hit in natija.points
    ]


if __name__ == "__main__":
    import sys

    savol = sys.argv[1] if len(sys.argv) > 1 else "PQ-500 qaror"
    print(f"Savol: {savol}\n")
    for b in qidir(savol):
        print(f"--- manba: {b.manba} (o'xshashlik: {b.score:.3f}) ---")
        print(f"    mavzu: {b.sarlavha[:90]}")
        print(b.matn[:400])
        print()
