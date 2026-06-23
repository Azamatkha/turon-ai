"""RAG sozlamalari (env'dan o'qiladi, qattiq yozilmagan).

Bular asosiy ilova Config'idan alohida — RAG mustaqil ishlaydi (CLI ingest ham).
"""
import os

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "turon_docs")
VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", "1024"))

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "uzb+rus")
OCR_DPI = int(os.getenv("OCR_DPI", "400"))

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
