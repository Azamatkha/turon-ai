"""Zaxira nusxalar: Qdrant snapshot, rotatsiya va ro'yxat.

Papka tuzilishi (config.app.BACKUP_DIR):
    postgres/db_YYYYMMDD_HHMMSS.dump        — pg_dump -Fc (`backup` konteyneri)
    postgres/last_status                    — "ok|fail <vaqt>" (o'sha konteyner)
    qdrant/<kolleksiya>_YYYYMMDD_HHMMSS.snapshot — Qdrant snapshot (Celery)
    qdrant/last_status

Postgres nusxasini ilova emas, alohida konteyner oladi: server PostgreSQL 18,
ilova obrazidagi pg_dump esa 15-versiya — eski pg_dump yangi serverni
dump qilishdan bosh tortadi.
"""

from datetime import UTC, datetime
from pathlib import Path
import time

import httpx

from loggers import get_logger
from src.main.config import config

logger = get_logger(__name__)

KINDS = ("postgres", "qdrant")
_SUFFIX = {"postgres": ".dump", "qdrant": ".snapshot"}


def backup_root() -> Path:
    return Path(config.app.BACKUP_DIR)


def _write_status(kind: str, ok: bool, note: str = "") -> None:
    path = backup_root() / kind / "last_status"
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    path.write_text(f"{'ok' if ok else 'fail'} {stamp} {note}".strip() + "\n", "utf-8")


def read_status(kind: str) -> tuple[str | None, str | None]:
    """(holat "ok"|"fail", ISO vaqt) — fayl bo'lmasa (None, None)."""
    try:
        parts = (backup_root() / kind / "last_status").read_text("utf-8").split()
    except OSError:
        return None, None
    return (parts[0] if parts else None), (parts[1] if len(parts) > 1 else None)


def rotate(kind: str, keep_days: int | None = None) -> int:
    """`keep_days` kundan eski nusxalarni o'chiradi. Har doim kamida eng
    so'nggi bittasi qoladi — nusxa olish to'xtab qolsa ham oxirgisi yo'qolmaydi."""
    keep = keep_days if keep_days is not None else config.app.BACKUP_KEEP_DAYS
    files = sorted(
        (backup_root() / kind).glob(f"*{_SUFFIX[kind]}"),
        key=lambda f: f.stat().st_mtime,
    )
    cutoff = time.time() - keep * 86400
    removed = 0
    for f in files[:-1]:
        if f.stat().st_mtime < cutoff:
            f.unlink(missing_ok=True)
            removed += 1
    return removed


def snapshot_qdrant() -> Path:
    """Qdrant kolleksiyasidan snapshot oladi va backup papkasiga yuklab oladi.

    Qdrant snapshot'ni o'z ichida (/qdrant/snapshots) yaratadi; biz uni
    yuklab olib, Qdrant tomonidagisini o'chiramiz — aks holda u Qdrant
    volume'ida to'planib boraveradi.
    """
    base = f"http://{config.qdrant.QDRANT_HOST}:{config.qdrant.QDRANT_PORT}"
    collection = config.qdrant.QDRANT_COLLECTION
    target_dir = backup_root() / "qdrant"
    target_dir.mkdir(parents=True, exist_ok=True)
    # trust_env=False: bank tarmog'idagi HTTP(S)_PROXY ichki `qdrant` xostiga
    # aralashmasin
    try:
        with httpx.Client(base_url=base, timeout=600, trust_env=False) as client:
            res = client.post(f"/collections/{collection}/snapshots", params={"wait": "true"})
            res.raise_for_status()
            name = res.json()["result"]["name"]

            stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            final = target_dir / f"{collection}_{stamp}.snapshot"
            part = final.with_suffix(".snapshot.part")
            with client.stream("GET", f"/collections/{collection}/snapshots/{name}") as dl:
                dl.raise_for_status()
                with part.open("wb") as fh:
                    for chunk in dl.iter_bytes(1024 * 1024):
                        fh.write(chunk)
            # Yarim yozilgan fayl hech qachon "tayyor nusxa" bo'lib ko'rinmasin
            part.replace(final)

            client.delete(f"/collections/{collection}/snapshots/{name}")
    except Exception as exc:
        _write_status("qdrant", ok=False, note=type(exc).__name__)
        raise
    _write_status("qdrant", ok=True)
    rotate("qdrant")
    logger.info("Qdrant snapshot saqlandi: %s (%d bayt)", final.name, final.stat().st_size)
    return final


def list_backups() -> list[tuple[str, str, int, datetime]]:
    """(tur, fayl nomi, hajm, yaratilgan vaqt) — yangisidan eskisiga."""
    items: list[tuple[str, str, int, datetime]] = []
    for kind in KINDS:
        folder = backup_root() / kind
        if not folder.is_dir():
            continue
        for f in folder.glob(f"*{_SUFFIX[kind]}"):
            st = f.stat()
            items.append((kind, f.name, st.st_size, datetime.fromtimestamp(st.st_mtime, UTC)))
    items.sort(key=lambda x: x[3], reverse=True)
    return items
