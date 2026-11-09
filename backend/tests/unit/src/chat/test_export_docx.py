from datetime import UTC, datetime
import io
from types import SimpleNamespace
from typing import Any
from uuid import uuid4
from xml.dom import minidom
import zipfile

import pytest

from src.chat.export_docx import ExportMessage, build_chat_docx, markdown_to_body
from src.chat.usecases import ExportSessionDocxUseCase
from src.core.errors.exceptions import InstanceNotFoundException


def _doc_xml(data: bytes) -> str:
    z = zipfile.ZipFile(io.BytesIO(data))
    for name in z.namelist():
        if name.endswith((".xml", ".rels")):
            minidom.parseString(z.read(name))  # har bir qism to'g'ri XML
    return z.read("word/document.xml").decode("utf-8")


def test_docx_is_valid_and_escapes() -> None:
    data = build_chat_docx(
        "Kredit <1>",
        [ExportMessage("user", 'a & b "c" \x01', None)],
        user_label="Siz", bot_label="Turon AI", meta_line="m",
    )
    doc = _doc_xml(data)
    assert "Kredit &lt;1&gt;" in doc and "a &amp; b" in doc


def test_markdown_table_list_bold() -> None:
    body = markdown_to_body("**Foiz:** 22%\n- bir\n| A | B |\n|---|---|\n| 1 | 2 |")
    assert body.count("<w:tbl>") == 1
    assert "<w:b/>" in body
    assert "•" in body
    assert "---" not in body


class _Repo:
    def __init__(self, session: Any) -> None:
        self.s = session

    async def get_single(self, session: Any, **kw: Any) -> Any:
        return self.s

    async def list_by_session(self, session: Any, session_id: Any) -> list:
        return [
            SimpleNamespace(role="user", content="Savol", created_at=datetime(2026, 11, 9, 5, 0, tzinfo=UTC)),
            SimpleNamespace(role="assistant", content="Javob", created_at=datetime(2026, 11, 9, 5, 1, tzinfo=UTC)),
        ]


class _Uow:
    def __init__(self, s: Any) -> None:
        self.chat_sessions = _Repo(s)
        self.chat_messages = self.chat_sessions
        self.session = None

    async def __aenter__(self) -> "_Uow":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None


@pytest.mark.asyncio
async def test_export_usecase_filename_and_local_time() -> None:
    uow = _Uow(SimpleNamespace(title='Kredit: "shartlar"?'))
    res = await ExportSessionDocxUseCase(uow).execute(uuid4(), uuid4(), "ru")  # type: ignore[arg-type]
    assert res.filename == "Kredit shartlar.docx"
    doc = _doc_xml(res.content)
    assert "Вы" in doc and "10:00" in doc  # 05:00 UTC -> 10:00 Toshkent


@pytest.mark.asyncio
async def test_export_other_users_session_not_found() -> None:
    with pytest.raises(InstanceNotFoundException):
        await ExportSessionDocxUseCase(_Uow(None)).execute(uuid4(), uuid4(), "uz")  # type: ignore[arg-type]
