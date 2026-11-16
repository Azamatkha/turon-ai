"""Face-ID loglari qidiruvi: so'z bo'yicha shart, '@' tashlanadi, jami soni
xuddi shu filtr bilan sanaladi."""

from typing import Any

import pytest
from sqlalchemy.dialects import postgresql

from src.user.repositories import FaceIdSignatureLogRepository


class _Result:
    def scalar_one(self) -> int:
        return 0

    def all(self) -> list[Any]:
        return []


class _Session:
    def __init__(self) -> None:
        self.sql: list[str] = []

    async def execute(self, stmt: Any) -> _Result:
        self.sql.append(str(stmt.compile(dialect=postgresql.dialect())))
        return _Result()


@pytest.mark.asyncio
async def test_search_words_and_count() -> None:
    session = _Session()
    repo = FaceIdSignatureLogRepository()
    await repo.list_with_usernames(session, only_failed=True, search="@ali 3120")  # type: ignore[arg-type]
    count_sql, list_sql = session.sql
    for sql in (count_sql, list_sql):
        # Ikki so'z — ikki guruh shart; claims JSON matn sifatida qidiriladi
        assert sql.count("CAST(face_id_signature_logs.claims AS TEXT)") == 2
        assert "face_id_signature_logs.result !=" in sql
        assert "users.username ILIKE" in sql
    assert "count(*)" in count_sql.lower()


@pytest.mark.asyncio
async def test_no_search_no_filter() -> None:
    session = _Session()
    await FaceIdSignatureLogRepository().list_with_usernames(session)  # type: ignore[arg-type]
    assert all("ILIKE" not in s and "WHERE" not in s for s in session.sql)
