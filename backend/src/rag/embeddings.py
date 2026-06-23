"""
3-QADAM: Matnni vektorga aylantirish (bge-m3 modeli).

Model OG'IR (~2.3 GB) — "bir marta yukla, ko'p marta ishlat": global o'zgaruvchida
saqlanadi va qayta ishlatiladi.
"""
from src.rag.config import EMBEDDING_MODEL

# Eslatma: sentence-transformers (va torch) OG'IR. Ilova ishga tushganda emas,
# faqat birinchi marta kerak bo'lganda import qilamiz.
_model = None


def model_ol():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        print(f"Embedding modeli yuklanyapti: {EMBEDDING_MODEL} (birinchi marta sekin)...")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def vektorla(matnlar: list[str]) -> list[list[float]]:
    """Matnlar ro'yxatini 1024 o'lchamli vektorlar ro'yxatiga aylantiradi."""
    return model_ol().encode(matnlar, normalize_embeddings=True).tolist()
