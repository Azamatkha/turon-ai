"""Hujjat tahlilchisi: fayl -> matn -> Qwen tahlili (oqim bilan).

Hodisalar `/v1/chat/ask/stream` bilan BIR XIL formatda (delta/status/done/
error), shuning uchun frontend o'sha SSE o'quvchisini ishlatadi.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from loggers import get_logger
from src.core.ai.interfaces import BaseAIClient
from src.documents.extractors import ExtractedDocument, extract_document
from src.documents.prompts import PART_NOTES_SYSTEM, analyze_prompt, analyze_system
from src.knowledge.chunking import chunk_text

logger = get_logger(__name__)

# Shundan qisqa matn modelga to'liq beriladi (~13-20k token: num_ctx 32k ga
# javob bilan birga sig'adi). Uzunrog'i bo'laklarga bo'linib, avval har
# bo'lakdan qisqa qaydlar olinadi.
DIRECT_MAX_CHARS = 40_000
PART_CHARS = 18_000
# Juda katta hujjat: ko'pi bilan shuncha bo'lak tahlil qilinadi
MAX_PARTS = 8
PART_NOTES_MAX_TOKENS = 900
ANSWER_MAX_TOKENS = 2048
TEMPERATURE = 0.2


class AnalyzeDocumentUseCase:
    def __init__(self, ai_client: BaseAIClient, convert_timeout: int) -> None:
        self.ai_client = ai_client
        self.convert_timeout = convert_timeout
        # Jurnal uchun (router o'qiydi)
        self.document: ExtractedDocument | None = None

    async def _condense(self, text: str) -> tuple[str, bool]:
        """Uzun hujjat: bo'laklardan qaydlar. Qaytaradi: (matn, qisqartirildimi)."""
        parts = chunk_text(text, max_chars=PART_CHARS, min_chars=PART_CHARS // 4)
        truncated = len(parts) > MAX_PARTS
        parts = parts[:MAX_PARTS]
        sem = asyncio.Semaphore(2)

        async def notes(i: int, part: str) -> str:
            async with sem:
                try:
                    out = await self.ai_client.generate_text(
                        f"<part index=\"{i + 1}/{len(parts)}\">\n{part}\n</part>",
                        system_prompt=PART_NOTES_SYSTEM,
                        temperature=0.1,
                        max_tokens=PART_NOTES_MAX_TOKENS,
                    )
                except Exception:  # noqa: BLE001 - bo'lak yo'qolmasin
                    logger.warning("[Doc] %d-bo'lak qaydlari olinmadi — boshi olinadi", i + 1)
                    out = part[:2500]
            return f"--- {i + 1}-qism ---\n{out.strip()}"

        results = await asyncio.gather(*(notes(i, p) for i, p in enumerate(parts)))
        return "\n\n".join(results), truncated

    async def stream(
        self, *, data: bytes, filename: str, question: str, lang: str
    ) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def progress(done: int, total: int) -> None:
            await queue.put(
                {"type": "status", "step": "doc_read", "done": done, "total": total}
            )

        yield {"type": "status", "step": "doc_read"}
        # Matn ajratish fon vazifasida — sahifa progressi shu orada oqimga chiqadi
        task = asyncio.create_task(
            extract_document(
                data,
                filename,
                self.ai_client,
                convert_timeout=self.convert_timeout,
                progress=progress,
            )
        )
        try:
            while not task.done():
                getter = asyncio.create_task(queue.get())
                finished, _ = await asyncio.wait(
                    {task, getter}, return_when=asyncio.FIRST_COMPLETED
                )
                if getter in finished:
                    yield getter.result()
                else:
                    getter.cancel()
            while not queue.empty():
                yield queue.get_nowait()
            doc = task.result()
        finally:
            if not task.done():
                task.cancel()
        self.document = doc

        notes: list[str] = []
        if doc.skipped_pages:
            notes.append(
                f"hujjatda {doc.pages} sahifa, shundan {doc.skipped_pages} tasi "
                "o'qilmadi (chegara) — tahlil o'qilgan qism bo'yicha"
            )
        if doc.ocr_pages:
            notes.append("ba'zi sahifalar skandan OCR bilan o'qilgan, xato bo'lishi mumkin")

        body = doc.text
        yield {"type": "status", "step": "doc_analyze"}
        if len(body) > DIRECT_MAX_CHARS:
            body, truncated = await self._condense(body)
            notes.append("hujjat uzun — quyida uning qismlari bo'yicha qaydlar berilgan")
            if truncated:
                notes.append("hujjat juda uzun, faqat boshidagi qismlar tahlil qilindi")

        prompt = analyze_prompt(
            filename=filename, document=body, question=question, note="; ".join(notes)
        )
        async for ev in self.ai_client.stream_generate(
            prompt,
            temperature=TEMPERATURE,
            max_tokens=ANSWER_MAX_TOKENS,
            system_prompt=analyze_system(lang),
        ):
            if ev.get("type") == "done":
                yield {
                    "type": "done",
                    "completion_tokens": int(ev.get("completion_tokens") or 0),
                    "finish_reason": str(ev.get("finish_reason") or ""),
                    "max_tokens": ANSWER_MAX_TOKENS,
                    "sources": [],
                }
            else:
                yield ev
