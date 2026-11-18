"""Hujjat tahlilchisi: matn ajratish va tahlil oqimi."""

from collections.abc import AsyncIterator
import io
from types import SimpleNamespace
from typing import Any
import zipfile

import pymupdf
import pytest

from src.core.errors.exceptions import InstanceProcessingException
from src.documents import extractors
from src.documents.extractors import docx_to_text, extract_document, xlsx_to_text
from src.documents.usecases import AnalyzeDocumentUseCase, direct_max_chars

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx(body: str) -> bytes:
    xml = f'<?xml version="1.0"?><w:document xmlns:w="{_W_NS}"><w:body>{body}</w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", xml)
    return buf.getvalue()


def _p(text: str) -> str:
    return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"


class FakeAI:
    def __init__(self, vision: bool = True, ctx: int | None = 32_768) -> None:
        self.vision = vision
        self.ctx = ctx
        self.images = 0
        self.prompts: list[str] = []
        self.systems: list[str] = []
        self.notes_calls = 0

    async def supports_vision(self) -> bool:
        return self.vision

    async def context_window(self) -> int | None:
        return self.ctx

    async def read_image(self, png: bytes, **_: Any) -> Any:
        self.images += 1
        return SimpleNamespace(text="BUYRUQ № 15\nSkan sahifa matni Qwen o'qidi")

    async def generate_text(self, prompt: str, **_: Any) -> str:
        self.notes_calls += 1
        return "qism qaydlari"

    async def stream_generate(
        self, prompt: str, *, system_prompt: str | None = None, **_: Any
    ) -> AsyncIterator[dict[str, Any]]:
        self.prompts.append(prompt)
        self.systems.append(system_prompt or "")
        yield {"type": "delta", "text": "### Hujjat turi\nBuyruq"}
        yield {"type": "done", "completion_tokens": 7, "finish_reason": "stop"}


def _pdf(pages: list[str]) -> bytes:
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_text((50, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_docx_paragraphs_and_table() -> None:
    table = (
        "<w:tbl><w:tr><w:tc>" + _p("Summa") + "</w:tc><w:tc>" + _p("5 000 000") + "</w:tc></w:tr></w:tbl>"
    )
    text = docx_to_text(_docx(_p("SHARTNOMA № 7") + table + _p("Muddat: 2026-12-31")))
    assert "SHARTNOMA № 7" in text
    assert "| Summa | 5 000 000 |" in text
    assert text.index("SHARTNOMA") < text.index("Summa") < text.index("Muddat")


def test_docx_wrong_format() -> None:
    with pytest.raises(InstanceProcessingException):
        docx_to_text(b"not a zip")


def test_xlsx_sheets_rows() -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Kreditlar"
    ws.append(["Mijoz", "Summa"])
    ws.append([None, None])
    ws.append(["Aliyev", 1500.0])
    buf = io.BytesIO()
    wb.save(buf)
    text = xlsx_to_text(buf.getvalue())
    assert "### Varaq: Kreditlar" in text
    assert "| Aliyev | 1500 |" in text
    assert "|  |" not in text


async def test_unsupported_and_empty() -> None:
    with pytest.raises(InstanceProcessingException):
        await extract_document(b"MZ..", "virus.exe", FakeAI(), convert_timeout=5)
    with pytest.raises(InstanceProcessingException):
        await extract_document(b"", "a.pdf", FakeAI(), convert_timeout=5)


async def test_pdf_text_page_direct_scan_page_vision() -> None:
    ai = FakeAI()
    long_line = "Ushbu nizom bank xodimlari uchun ichki tartib qoidalarini belgilaydi va majburiy"
    progress: list[tuple[int, int]] = []

    async def on_progress(done: int, total: int) -> None:
        progress.append((done, total))

    doc = await extract_document(
        _pdf([long_line, ""]), "nizom.pdf", ai, convert_timeout=5, progress=on_progress
    )
    # Matnli sahifa modelga yuborilmaydi, faqat skan sahifa
    assert ai.images == 1
    assert doc.vision_pages == 1 and doc.ocr_pages == 0
    assert "bank xodimlari" in doc.text and "Qwen o'qidi" in doc.text
    assert progress[0] == (0, 1) and progress[-1] == (1, 1)


async def test_pdf_scan_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extractors, "MAX_SCAN_PAGES", 2)
    ai = FakeAI()
    doc = await extract_document(_pdf(["", "", ""]), "skan.pdf", ai, convert_timeout=5)
    assert ai.images == 2
    assert doc.skipped_pages == 1 and doc.pages == 3


async def test_scan_falls_back_to_ocr_without_vision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extractors, "ocr_png", lambda png: "Tesseract matni zaxira yo'li")
    ai = FakeAI(vision=False)
    doc = await extract_document(_pdf([""]), "skan.pdf", ai, convert_timeout=5)
    assert ai.images == 0
    assert doc.ocr_pages == 1
    assert "Tesseract" in doc.text


async def _collect(it: AsyncIterator[dict[str, Any]]) -> list[dict[str, Any]]:
    return [ev async for ev in it]


async def test_analyze_stream_events_and_prompt() -> None:
    ai = FakeAI()
    uc = AnalyzeDocumentUseCase(ai_client=ai, convert_timeout=5)  # type: ignore[arg-type]
    events = await _collect(
        uc.stream(
            data=_docx(_p("Ariza. Menga mehnat ta'tili berishingizni so'rayman.")),
            filename="ariza.docx",
            question="kimga yozilgan?",
            lang="ru",
        )
    )
    types = [e["type"] for e in events]
    assert types[0] == "status" and "delta" in types and types[-1] == "done"
    assert {"doc_read", "doc_analyze"} <= {e.get("step") for e in events}
    assert events[-1]["sources"] == [] and events[-1]["completion_tokens"] == 7
    assert "<document>" in ai.prompts[0] and "kimga yozilgan?" in ai.prompts[0]
    assert "РУССКОМ" in ai.systems[0]
    assert uc.document is not None and uc.document.kind == "docx"


async def test_long_document_condensed() -> None:
    ai = FakeAI()
    uc = AnalyzeDocumentUseCase(ai_client=ai, convert_timeout=5)  # type: ignore[arg-type]
    para = "Bu bandda bankning majburiyatlari batafsil yozilgan. " * 40
    limit = direct_max_chars(32_768)
    text = "\n\n".join([para] * (limit // len(para) + 5))
    await _collect(uc.stream(data=text.encode(), filename="katta.txt", question="", lang="uz"))
    assert ai.notes_calls >= 2
    assert "qism qaydlari" in ai.prompts[0]
    assert len(ai.prompts[0]) < limit


async def test_64k_context_fits_doc_without_condensing() -> None:
    # 32k da bo'laklanadigan hujjat 65536 oynada butunligicha beriladi
    ai = FakeAI(ctx=65_536)
    uc = AnalyzeDocumentUseCase(ai_client=ai, convert_timeout=5)  # type: ignore[arg-type]
    para = "Kredit shartnomasi bandi, foiz stavkasi va muddatlar. " * 40
    text = "\n\n".join([para] * (direct_max_chars(32_768) // len(para) + 5))
    await _collect(uc.stream(data=text.encode(), filename="katta.txt", question="", lang="uz"))
    assert ai.notes_calls == 0
    assert len(ai.prompts[0]) > direct_max_chars(32_768)


def test_direct_max_chars_scales_with_context() -> None:
    assert direct_max_chars(65_536) > direct_max_chars(32_768) * 2
    assert direct_max_chars(None) == direct_max_chars(32_768)
    assert direct_max_chars(4_096) == 20_000


def test_xlsx_leading_empty_columns_and_dates() -> None:
    from datetime import datetime

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Oktabr"
    ws["C2"] = "Filial"
    ws["D2"] = "Sana"
    ws["C3"] = "Buxoro BXM"
    ws["D3"] = datetime(2026, 10, 1)
    buf = io.BytesIO()
    wb.save(buf)
    text = xlsx_to_text(buf.getvalue())
    assert "### Varaq: Oktabr (2 qator, 2 ustun)" in text
    assert "| Buxoro BXM | 2026-10-01 |" in text
