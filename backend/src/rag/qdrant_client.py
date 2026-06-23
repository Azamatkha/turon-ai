"""
Qdrant (vektor baza) bilan ulanish va kolleksiyani tayyorlash.

Ulanish manzili env'dan (docker ichida QDRANT_HOST=qdrant). Kolleksiya:
1024 o'lchamli COSINE vektorlar.
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from src.rag.config import QDRANT_COLLECTION, QDRANT_HOST, QDRANT_PORT, VECTOR_SIZE

COLLECTION = QDRANT_COLLECTION

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def collection_tayyorla() -> None:
    """Kolleksiya yo'q bo'lsa yaratadi (bor bo'lsa tegmaydi)."""
    mavjud = [c.name for c in client.get_collections().collections]
    if COLLECTION not in mavjud:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"'{COLLECTION}' kolleksiyasi yaratildi")
    else:
        print(f"'{COLLECTION}' kolleksiyasi allaqachon bor")
