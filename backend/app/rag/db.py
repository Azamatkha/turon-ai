import os                                  # docker'dan sozlamalarni o'qish uchun
from qdrant_client import QdrantClient     # Qdrant bazasi bilan bog'lanish vositasi
from qdrant_client.models import Distance, VectorParams   # kolleksiya sozlamalari

COLLECTION = "turon_docs"   # bazadagi "jadval" nomi
VEKTOR_OLCHAMI = 1024       # bge-m3 har matnga 1024 ta raqam beradi -> baza ham 1024 kutadi

# Qdrant'ga ulanish "trubkasi":
client = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),  # docker ichida "qdrant", aks holda "localhost"
    port=int(os.getenv("QDRANT_PORT", "6333")),  # Qdrant porti
)
# ↑ os.getenv -> manzilni docker-compose.yml dagi sozlamadan oladi (qattiq yozilmagan).


def collection_tayyorla():
    mavjud = [c.name for c in client.get_collections().collections]  # mavjud kolleksiyalar
    if COLLECTION not in mavjud:                     # agar "turon_docs" hali yo'q bo'lsa:
        client.create_collection(                    # yangisini yaratamiz
            collection_name=COLLECTION,
            vectors_config=VectorParams(
                size=VEKTOR_OLCHAMI,                  # 1024 o'lchamli vektorlar
                distance=Distance.COSINE,            # o'xshashlikni o'lchash usuli (COSINE)
            ),
        )
        print(f"'{COLLECTION}' kolleksiyasi yaratildi")
    else:
        print(f"'{COLLECTION}' kolleksiyasi allaqachon bor")   # bor bo'lsa tegmaydi
# ↑ Baza "jadvali" yo'q bo'lsa yaratadi. COSINE = vektorlar yo'nalishi qanchalik o'xshash.