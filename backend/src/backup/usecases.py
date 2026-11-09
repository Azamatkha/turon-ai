from datetime import datetime

from src.backup.schemas import BackupFileView, BackupKindStatus, BackupOverviewView
from src.backup.services import KINDS, backup_root, list_backups, read_status
from src.main.config import config


class BackupOverviewUseCase:
    """Zaxira nusxalar holati: har tur bo'yicha oxirgi natija va fayllar."""

    def execute(self) -> BackupOverviewView:
        files = list_backups()
        statuses: list[BackupKindStatus] = []
        for kind in KINDS:
            mine = [f for f in files if f[0] == kind]
            result, at = read_status(kind)
            statuses.append(
                BackupKindStatus(
                    kind=kind,
                    last_result=result,
                    last_run_at=_parse_dt(at),
                    latest_at=mine[0][3] if mine else None,
                    count=len(mine),
                    total_size=sum(f[2] for f in mine),
                )
            )
        return BackupOverviewView(
            keep_days=config.app.BACKUP_KEEP_DAYS,
            available=backup_root().is_dir(),
            statuses=statuses,
            files=[
                BackupFileView(kind=k, name=n, size=s, created_at=c)
                for k, n, s, c in files
            ],
        )


class TriggerQdrantBackupUseCase:
    """Qdrant snapshot'ini hoziroq navbatga qo'yadi (Celery worker oladi)."""

    def execute(self) -> None:
        # Import shu yerda: router yuklanganda Celery ilovasi kerak bo'lmasin
        from src.backup.tasks import backup_qdrant

        backup_qdrant.delay()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
