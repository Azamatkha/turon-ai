from datetime import datetime

from src.core.schemas import Base


class BackupFileView(Base):
    # "postgres" | "qdrant"
    kind: str
    name: str
    size: int
    created_at: datetime


class BackupKindStatus(Base):
    kind: str
    # Oxirgi urinish natijasi: "ok" | "fail" | None (hali bo'lmagan)
    last_result: str | None = None
    last_run_at: datetime | None = None
    # Eng so'nggi tayyor nusxa
    latest_at: datetime | None = None
    count: int = 0
    total_size: int = 0


class BackupOverviewView(Base):
    keep_days: int
    # Papka umuman yo'q — volume ulanmagan (masalan lokal ishga tushirishda)
    available: bool
    statuses: list[BackupKindStatus]
    files: list[BackupFileView]
