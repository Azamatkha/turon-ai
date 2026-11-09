from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from src.chat.repositories import ChatSessionRepository
from src.chat.usecases import SearchMessagesUseCase, _like_pattern, _snippet


def test_like_pattern_escapes_wildcards() -> None:
    assert _like_pattern("50%") == "%50\\%%"
    assert _like_pattern("a_b") == "%a\\_b%"
    assert _like_pattern("c:\\x") == "%c:\\\\x%"


def test_snippet_centers_on_match() -> None:
    text = "boshi " * 30 + "Kredit foizi 22%" + " oxiri" * 30
    snip = _snippet(text, ["kredit"])
    assert "Kredit foizi 22%" in snip
    assert snip.startswith("…") and snip.endswith("…")
    assert len(snip) <= 125


def test_snippet_without_match_takes_start() -> None:
    assert _snippet("Qisqa matn", ["yo'q"]) == "Qisqa matn"


class _FakeRepo:
    def __init__(self) -> None:
        self.patterns: list[str] = []

    async def search_messages(self, session: Any, user_id: Any, patterns: list[str], limit: int) -> list:
        self.patterns = patterns
        msg = SimpleNamespace(
            id=uuid4(), session_id=uuid4(), role="assistant",
            content="Кредит фоизи йилига 22%", created_at=datetime.now(UTC),
        )
        return [(msg, "Kredit haqida")]


class _FakeUow:
    def __init__(self) -> None:
        self.chat_sessions = _FakeRepo()
        self.session = None

    async def __aenter__(self) -> "_FakeUow":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None


@pytest.mark.asyncio
async def test_search_uses_latin_and_cyrillic() -> None:
    uow = _FakeUow()
    hits = await SearchMessagesUseCase(uow).execute(uuid4(), "kredit foizi")  # type: ignore[arg-type]
    assert "%kredit foizi%" in uow.chat_sessions.patterns
    assert "%кредит фоизи%" in uow.chat_sessions.patterns
    assert hits[0].session_title == "Kredit haqida"
    assert "Кредит фоизи" in hits[0].snippet


@pytest.mark.asyncio
async def test_search_too_short_returns_empty() -> None:
    uow = _FakeUow()
    assert await SearchMessagesUseCase(uow).execute(uuid4(), " a ") == []  # type: ignore[arg-type]
    assert uow.chat_sessions.patterns == []


@pytest.mark.asyncio
async def test_query_filters_owner_and_deleted() -> None:
    captured: dict[str, Any] = {}

    class _Session:
        async def execute(self, query: Any) -> Any:
            captured["sql"] = str(query.compile(dialect=postgresql.dialect()))
            return SimpleNamespace(all=lambda: [])

    await ChatSessionRepository().search_messages(_Session(), uuid4(), ["%x%"])  # type: ignore[arg-type]
    sql = captured["sql"]
    assert "chat_sessions.user_id" in sql
    assert "chat_sessions.is_deleted IS false" in sql
    assert "ILIKE" in sql and "ESCAPE" in sql
