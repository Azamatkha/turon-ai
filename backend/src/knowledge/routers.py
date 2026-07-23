"""Knowledge base upload endpoint.

SWAGGER'DA TEKSHIRISH:
1) admin bilan login qiling, "Authorize" ga tokenni kiriting.
2) POST /v1/admin/knowledge/upload -> {"title": "...", "text": "..."}
3) Qdrant dashboard (http://localhost:6333/dashboard) da point paydo bo'ladi.
"""

import base64
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile
from redis.asyncio import Redis

from src.core.ai.dependencies import get_ai_client
from src.core.ai.embeddings import OllamaEmbedder, get_embedder
from src.core.ai.interfaces import BaseAIClient
from src.core.errors.exceptions import (
    InstanceNotFoundException,
    InstanceProcessingException,
)
from src.core.redis.dependencies import get_redis_client
from src.core.schemas import SuccessResponse
from src.core.vectorstore.dependencies import get_vector_store
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge.pdf_jobs import get_status, save_pdf, set_status
from src.knowledge.schemas import (
    AnswerResult,
    EmployeeIn,
    KnowledgeDetail,
    KnowledgeItem,
    PdfJobAccepted,
    PdfJobStatus,
    PdfOcrCompareResult,
    QuestionRequest,
    ScrapeRequest,
    UpdateKnowledgeRequest,
    UploadResult,
    UploadTextRequest,
)
from src.knowledge.tasks import process_pdf
from src.knowledge.usecases import (
    AnswerQuestionUseCase,
    DeleteKnowledgeUseCase,
    GetKnowledgeDetailUseCase,
    ListKnowledgeUseCase,
    ScrapeUrlUseCase,
    UpdateKnowledgeUseCase,
    UploadEmployeesUseCase,
    UploadKnowledgeUseCase,
)
from src.main.config import config
from src.user.auth.permissions.checker import require_permission
from src.user.auth.permissions.enum import Permission
from src.user.models import User

router = APIRouter()


@router.get("", response_model=list[KnowledgeItem])
async def list_knowledge(
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
) -> list[KnowledgeItem]:
    """Admin: yuklangan ma'lumotlar ro'yxati (sarlavha bo'yicha guruhlangan)."""
    use_case = ListKnowledgeUseCase(store=store)
    return await use_case.execute()


@router.delete("", response_model=SuccessResponse)
async def delete_knowledge(
    title: str,
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
) -> SuccessResponse:
    """Admin: bitta sarlavha ostidagi barcha bo'laklarni o'chiradi."""
    await DeleteKnowledgeUseCase(store=store).execute(title=title)
    return SuccessResponse(success=True)


@router.put("", response_model=UploadResult)
async def update_knowledge(
    data: UpdateKnowledgeRequest,
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    embedder: Annotated[OllamaEmbedder, Depends(get_embedder)],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
) -> UploadResult:
    """Admin: ma'lumotni tahrirlash (eski bo'laklarni o'chirib, qayta yozadi)."""
    use_case = UpdateKnowledgeUseCase(embedder=embedder, store=store)
    return await use_case.execute(
        old_title=data.old_title, title=data.title, text=data.text
    )


@router.get("/detail", response_model=KnowledgeDetail)
async def knowledge_detail(
    title: str,
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
) -> KnowledgeDetail:
    """Admin: bitta sarlavha ostidagi barcha bo'laklar (to'liq matn)."""
    use_case = GetKnowledgeDetailUseCase(store=store)
    return await use_case.execute(title=title)


@router.post("/ask", response_model=AnswerResult)
async def ask_knowledge(
    data: QuestionRequest,
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    embedder: Annotated[OllamaEmbedder, Depends(get_embedder)],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
    ai_client: Annotated[BaseAIClient, Depends(get_ai_client)],
) -> AnswerResult:
    """Admin test: savol -> Qdrant qidiruv -> Qwen javob (RAG)."""
    use_case = AnswerQuestionUseCase(
        embedder=embedder, store=store, ai_client=ai_client
    )
    return await use_case.execute(question=data.question, history=data.history)


@router.post("/upload", response_model=UploadResult)
async def upload_knowledge(
    data: UploadTextRequest,
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    embedder: Annotated[OllamaEmbedder, Depends(get_embedder)],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
) -> UploadResult:
    """Admin: matnni bo'laklarga bo'lib, embed qilib, sarlavha bilan Qdrant'ga yozadi."""
    use_case = UploadKnowledgeUseCase(embedder=embedder, store=store)
    return await use_case.execute(title=data.title, text=data.text)


@router.post("/pdf-ocr-test", response_model=PdfOcrCompareResult)
async def pdf_ocr_test(
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    file: Annotated[UploadFile, File()],
    page: Annotated[int, Form()] = 0,
) -> PdfOcrCompareResult:
    """Diagnostika: bitta PDF sahifasini uch usulda o'qib solishtiradi —
    PDF matn qatlami, Tesseract OCR va vision model (qwen3-vl). Qaysi biri
    yaxshiroq o'qishini ko'rish uchun (bazaga hech narsa yozmaydi).

    DIQQAT: vision va OCR sekin — bitta sahifa uchun bir necha o'n soniya."""
    import time

    from src.knowledge.pdf_extractor import extract_single_page, render_page_png
    from src.knowledge.vision_ocr import vision_ocr_timed

    content = await file.read()

    # PDF baytlaridan sahifalar sonini ham bilish uchun matn qatlami/OCR'ni
    # bitta ochishda olamiz.
    t0 = time.monotonic()
    text_layer, tesseract_text = extract_single_page(content, page)
    tesseract_ms = int((time.monotonic() - t0) * 1000)

    png = render_page_png(content, page)
    vision_text, vision_ms = await vision_ocr_timed(png)

    # Sahifalar sonini alohida olmaslik uchun render_page_png ichida tekshirildi;
    # bu yerda hujjatni yana ochib page_count olamiz (arzon).
    import fitz  # PyMuPDF

    doc = fitz.open(stream=content, filetype="pdf")
    try:
        page_count = doc.page_count
    finally:
        doc.close()

    return PdfOcrCompareResult(
        page=page,
        page_count=page_count,
        text_layer=text_layer,
        tesseract_text=tesseract_text,
        tesseract_ms=tesseract_ms,
        vision_text=vision_text,
        vision_ms=vision_ms,
        vision_model=config.ai.OLLAMA_VISION_MODEL,
    )


@router.post("/pdf", response_model=PdfJobAccepted)
async def upload_pdf(
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    redis: Annotated[Redis, Depends(get_redis_client)],
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()] = "",
) -> PdfJobAccepted:
    """Admin: PDF hujjatni yuklaydi (fon rejimida).

    OCR + LLM tozalash daqiqalab ketadi, korporativ proxy esa so'rovni 60
    soniyada uzadi — shuning uchun ish Celery ishchisiga topshiriladi. Bu
    endpoint darrov `job_id` qaytaradi; holatni `GET /pdf-status/{job_id}`
    orqali kuzatiladi.

    `title` bo'sh bo'lsa — hujjat mavzusi avtomatik aniqlanadi."""
    content = await file.read()
    if not content:
        raise InstanceProcessingException("Bo'sh fayl yuklandi.")

    job_id = uuid4().hex
    await save_pdf(redis, job_id, base64.b64encode(content).decode("ascii"))
    await set_status(redis, job_id, state="queued", message="Navbatda…")
    process_pdf.delay(job_id, file.filename or "", title)
    return PdfJobAccepted(job_id=job_id)


@router.get("/pdf-status/{job_id}", response_model=PdfJobStatus)
async def pdf_status(
    job_id: str,
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    redis: Annotated[Redis, Depends(get_redis_client)],
) -> PdfJobStatus:
    """Fon PDF ishlash holatini qaytaradi (frontend har necha soniyada so'raydi)."""
    status = await get_status(redis, job_id)
    if status is None:
        raise InstanceNotFoundException(
            "Topshiriq topilmadi — muddati o'tgan yoki noto'g'ri."
        )
    return PdfJobStatus(**status)


@router.post("/employees", response_model=UploadResult)
async def upload_employees(
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    embedder: Annotated[OllamaEmbedder, Depends(get_embedder)],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
    file: Annotated[UploadFile, File()],
) -> UploadResult:
    """Admin: xodimlar Excel (.xlsx) faylini o'qib, har xodimni alohida
    (doc_type=employee) Qdrant'ga yozadi. Har sheet — bir bo'lim."""
    content = await file.read()
    use_case = UploadEmployeesUseCase(embedder=embedder, store=store)
    return await use_case.execute(file_bytes=content)


@router.get("/employee-stats")
async def employee_stats(
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
) -> dict[str, Any]:
    """Diagnostika: bazada xodim (doc_type=employee) nuqtalari bor-yo'qligini
    va bo'limlar bo'yicha sonini ko'rsatadi."""
    recs = await store.scroll_all_records(limit=10000)
    emps = [p for _, p in recs if p.get("doc_type") == "employee"]
    depts: dict[str, int] = {}
    for p in emps:
        d = str(p.get("department", "?"))
        depts[d] = depts.get(d, 0) + 1
    sample = emps[0] if emps else None
    return {
        "total_points": len(recs),
        "employee_count": len(emps),
        "departments": depts,
        "sample": (
            {k: sample.get(k) for k in ("doc_type", "department", "fish", "ip", "phone")}
            if sample
            else None
        ),
    }


@router.post("/employees-json", response_model=UploadResult)
async def upload_employees_json(
    data: list[EmployeeIn],
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    embedder: Annotated[OllamaEmbedder, Depends(get_embedder)],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
) -> UploadResult:
    """Admin: xodimlarni tayyor JSON ro'yxati orqali yozadi (Excel'siz —
    openpyxl kerak emas). Body: [{department, division, position, fish, ip, phone}, ...]."""
    records = [r.model_dump() for r in data]
    use_case = UploadEmployeesUseCase(embedder=embedder, store=store)
    return await use_case.execute_records(records=records)


@router.post("/scrape", response_model=UploadResult)
async def scrape_url(
    data: ScrapeRequest,
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    embedder: Annotated[OllamaEmbedder, Depends(get_embedder)],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
) -> UploadResult:
    """Admin test: bitta URL'ni ochib, toza matnini ajratib, Qdrant'ga yozadi."""
    use_case = ScrapeUrlUseCase(embedder=embedder, store=store)
    return await use_case.execute(url=data.url)
