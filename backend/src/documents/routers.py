"""
Hujjat tahlilchisi endpointi (YANGI — mavjud /ask, /ask/stream o'zgarmagan).

─── SWAGGER'DA QANDAY TEKSHIRISH ───────────────────────────────────────────
1) /v1/users/auth/login orqali access_token oling va "Authorize" ga kiriting.
2) POST /v1/chat/analyze-document — `file` ga PDF/Word/Excel/rasm tanlang,
   ixtiyoriy `question` ("muddati qachon tugaydi?") va `lang` (uz|uz_cyrl|ru).
   Javob — SSE oqim: status (doc_read / doc_analyze), delta, done yoki error.
─────────────────────────────────────────────────────────────────────────────
"""

from collections.abc import AsyncIterator
import json
import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from loggers import get_logger
from src.chat.usecases import QuestionLogEntry, log_question
from src.core.ai.dependencies import get_ai_client
from src.core.ai.interfaces import BaseAIClient
from src.core.errors.exceptions import (
    InfrastructureException,
    InstanceProcessingException,
)
from src.core.limiter.depends import RateLimiter
from src.core.storage.media import read_upload_limited
from src.documents.usecases import AnalyzeDocumentUseCase
from src.main.config import config
from src.user.auth.dependencies import get_current_user, get_user_id_from_token
from src.user.models import User

router = APIRouter()
logger = get_logger(__name__)

# Hujjat tahlili oddiy savoldan ancha qimmat (skan sahifalar ham model orqali)
ANALYZE_RATE_LIMIT = RateLimiter(times=6, minutes=1, identifier=get_user_id_from_token)

_ERROR_TEXT = "Hujjatni tahlil qilishda xatolik yuz berdi. Bir oz kutib, qayta urinib ko'ring."


def _sse(ev: dict[str, Any]) -> str:
    return f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"


@router.post("/analyze-document", dependencies=[Depends(ANALYZE_RATE_LIMIT)])
async def analyze_document(
    file: Annotated[UploadFile, File(description="PDF, Word, Excel, PowerPoint, rasm yoki matn")],
    current_user: Annotated[User, Depends(get_current_user)],
    ai_client: Annotated[BaseAIClient, Depends(get_ai_client)],
    question: Annotated[str, Form(max_length=2000)] = "",
    lang: Annotated[str, Form(pattern="^(uz|uz_cyrl|ru)$")] = "uz",
) -> StreamingResponse:
    """Hujjat turini aniqlaydi va qisqa tahlil beradi. Fayl saqlanmaydi va
    bilim bazasiga yozilmaydi."""
    # Hajm oqim BOSHLANISHIDAN oldin tekshiriladi — 413 oddiy HTTP xato bo'lib qaytadi
    data = await read_upload_limited(file, config.app.DOC_ANALYZE_MAX_BYTES)
    filename = (file.filename or "hujjat").strip()[:200]
    use_case = AnalyzeDocumentUseCase(
        ai_client=ai_client, convert_timeout=config.app.CONVERT_TIMEOUT_SECONDS
    )

    async def event_stream() -> AsyncIterator[str]:
        started = time.monotonic()
        outcome = "answered"
        tokens = 0
        answer = ""
        try:
            async for ev in use_case.stream(
                data=data, filename=filename, question=question, lang=lang
            ):
                if ev.get("type") == "delta":
                    answer += str(ev.get("text") or "")
                elif ev.get("type") == "done":
                    tokens = int(ev.get("completion_tokens") or 0)
                yield _sse(ev)
        except InstanceProcessingException as exc:
            # Foydalanuvchiga tushunarli sabab (tur qo'llanmaydi, fayl buzilgan...)
            outcome = "no_info"
            yield _sse({"type": "error", "message": str(exc)})
        except InfrastructureException as exc:
            outcome = "error"
            logger.error("Hujjat tahlili uzildi: %s | %r", exc, filename)
            yield _sse({"type": "error", "message": _ERROR_TEXT})
        except Exception:  # noqa: BLE001 - oqim uzilsa, klientga xabar beramiz
            outcome = "error"
            logger.exception("Hujjat tahlili uzildi: %r", filename)
            yield _sse({"type": "error", "message": _ERROR_TEXT})

        doc = use_case.document
        await log_question(
            QuestionLogEntry(
                user_id=current_user.id,
                question=f"📎 {filename}" + (f" — {question.strip()}" if question.strip() else ""),
                intent="document",
                outcome=outcome,
                top_score=None,
                sources_count=0,
                completion_tokens=tokens,
                duration_ms=int((time.monotonic() - started) * 1000),
                answer=answer or None,
                verdict_note=(
                    f"{doc.kind}: {doc.pages} sahifa, vision {doc.vision_pages}, "
                    f"OCR {doc.ocr_pages}, {len(doc.text)} belgi"
                    if doc is not None
                    else None
                ),
            )
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
