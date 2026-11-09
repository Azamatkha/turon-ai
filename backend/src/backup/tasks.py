"""Kunlik vazifa: Qdrant (bilim bazasi) snapshot'ini oladi.

Postgres nusxasini bu vazifa OLMAYDI — uni alohida `backup` konteyneri
oladi (sababi: src/backup/services.py tepasidagi izoh).
"""

from celery_tasks.main import celery_app  # noqa: F401
from celery_tasks.types import typed_shared_task
from loggers import get_logger
from src.backup.services import snapshot_qdrant

logger = get_logger(__name__)


@typed_shared_task(name="backup_qdrant")
def backup_qdrant() -> str:
    path = snapshot_qdrant()
    return f"Saved {path.name}"
