"""Knowledge base upload endpoint.

SWAGGER'DA TEKSHIRISH:
1) admin bilan login qiling, "Authorize" ga tokenni kiriting.
2) POST /v1/admin/knowledge/upload -> {"title": "...", "text": "..."}
3) Qdrant dashboard (http://localhost:6333/dashboard) da point paydo bo'ladi.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, UploadFile

from src.core.ai.dependencies import get_ai_client
from src.core.ai.embeddings import OllamaEmbedder, get_embedder
from src.core.ai.interfaces import BaseAIClient
from src.core.schemas import SuccessResponse
from src.core.vectorstore.dependencies import get_vector_store
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge.schemas import (
    AnswerResult,
    EmployeeIn,
    KnowledgeDetail,
    KnowledgeItem,
    PdfUploadResult,
    QuestionRequest,
    ScrapeRequest,
    UpdateKnowledgeRequest,
    UploadResult,
    UploadTextRequest,
)
from src.knowledge.usecases import (
    AnswerQuestionUseCase,
    DeleteKnowledgeUseCase,
    GetKnowledgeDetailUseCase,
    ListKnowledgeUseCase,
    ScrapeUrlUseCase,
    UpdateKnowledgeUseCase,
    UploadEmployeesUseCase,
    UploadKnowledgeUseCase,
    UploadPdfUseCase,
)
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


@router.post("/pdf", response_model=PdfUploadResult)
async def upload_pdf(
    current_user: Annotated[
        User, Depends(require_permission(Permission.EDIT_SETTINGS))
    ],
    embedder: Annotated[OllamaEmbedder, Depends(get_embedder)],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
    ai_client: Annotated[BaseAIClient, Depends(get_ai_client)],
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()] = "",
) -> PdfUploadResult:
    """Admin: PDF hujjatni yuklaydi.

    Matn qatlami bo'lsa to'g'ridan-to'g'ri o'qiladi, skanerlangan sahifalar
    Tesseract OCR orqali o'tadi. So'ng LLM imzo/muhr/OCR shovqinini olib
    tashlaydi va natija bazaga yoziladi. `title` bo'sh bo'lsa — hujjat mavzusi
    avtomatik aniqlanadi.

    DIQQAT: OCR va tozalash sekin — ko'p sahifali hujjat bir necha daqiqa
    olishi mumkin."""
    content = await file.read()
    use_case = UploadPdfUseCase(embedder=embedder, store=store, ai_client=ai_client)
    return await use_case.execute(
        file_bytes=content, filename=file.filename or "", title=title
    )


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
