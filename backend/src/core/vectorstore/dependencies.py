from src.core.vectorstore.qdrant_store import QdrantStore

# Reuse a single client across requests (the Qdrant client holds a connection pool).
_store: QdrantStore | None = None


def get_vector_store() -> QdrantStore:
    global _store
    if _store is None:
        _store = QdrantStore()
    return _store
