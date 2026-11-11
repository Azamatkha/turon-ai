"""
Chat (suhbat) endpointlari. Hammasi joriy foydalanuvchiga tegishli — boshqaning
suhbatini ko'rib/o'zgartirib bo'lmaydi (get_single user_id bilan filtrlanadi).

─── SWAGGER'DA QANDAY TEKSHIRISH ───────────────────────────────────────────
1) /v1/users/auth/login orqali kirib, access_token oling.
2) Swagger tepasidagi "Authorize" tugmasiga tokenni kiriting (Bearer).
3) POST /v1/chat/sessions   body: {"title": "Birinchi suhbat"}      -> 201, sessiya id
4) GET  /v1/chat/sessions                                          -> ro'yxat (1 ta)
5) POST /v1/chat/sessions/{id}/messages  {"role":"user","content":"Salom"}  -> 201
6) POST /v1/chat/sessions/{id}/messages  {"role":"assistant","content":"Salom!"}
7) GET  /v1/chat/sessions/{id}            -> sessiya + ikkala xabar (vaqt tartibida)
8) PATCH /v1/chat/sessions/{id}  {"title":"Yangi nom"}             -> nom o'zgaradi
9) DELETE /v1/chat/sessions/{id}                                    -> {"success": true}
─────────────────────────────────────────────────────────────────────────────
"""

from collections.abc import AsyncIterator
import json
import re
import time
from typing import Annotated, Any
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from redis.asyncio import Redis

from loggers import get_logger
from src.chat.answer_cache import cached_answer_stream
from src.chat.schemas import (
    AddMessageModel,
    CreateSessionModel,
    GenerateTitleRequest,
    GenerateTitleResult,
    MessageSearchHit,
    MessageView,
    PinSessionModel,
    RenameSessionModel,
    SessionDetailView,
    SessionView,
    SuggestFollowupsRequest,
    SuggestFollowupsResult,
    VoteMessageModel,
)
from src.chat.usecases import (
    AddMessageUseCase,
    CreateSessionUseCase,
    DeleteMessageUseCase,
    DeleteSessionUseCase,
    ExportSessionDocxUseCase,
    GenerateTitleUseCase,
    GetSessionUseCase,
    ListSessionsUseCase,
    LoadHistoryUseCase,
    PinSessionUseCase,
    QuestionLogEntry,
    RenameSessionUseCase,
    SearchMessagesUseCase,
    SuggestFollowupsUseCase,
    VoteMessageUseCase,
    get_add_message_use_case,
    get_create_session_use_case,
    get_delete_message_use_case,
    get_delete_session_use_case,
    get_export_session_docx_use_case,
    get_generate_title_use_case,
    get_get_session_use_case,
    get_list_sessions_use_case,
    get_load_history_use_case,
    get_pin_session_use_case,
    get_rename_session_use_case,
    get_search_messages_use_case,
    get_suggest_followups_use_case,
    get_vote_message_use_case,
    log_question,
    notify_safety_flag,
)
from src.core.ai.dependencies import get_ai_client
from src.core.ai.embeddings import OllamaEmbedder, get_embedder
from src.core.ai.interfaces import BaseAIClient
from src.core.errors.exceptions import InfrastructureException
from src.core.limiter.depends import RateLimiter
from src.core.redis.dependencies import get_redis_client
from src.core.schemas import SuccessResponse
from src.core.vectorstore.dependencies import get_vector_store
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge.rates_scraper import RATES_TITLE
from src.knowledge.schemas import (
    AnswerResult,
    ChatTurn,
    QuestionRequest,
    RatesResult,
)
from src.knowledge.usecases import AnswerQuestionUseCase
from src.translator.usecases import TranslatorUseCase, get_translator_use_case
from src.user.auth.dependencies import get_current_user, get_user_id_from_token
from src.user.models import User

router = APIRouter()
logger = get_logger(__name__)


# ── LLM endpointlari uchun tezlik cheklovi ────────────────────────────────
# NEGA KERAK: /ask va /ask/stream — ilovadagi ENG QIMMAT endpointlar, chunki
# ular Ollama'da inference ishga tushiradi. Ilgari ular faqat `get_current_user`
# bilan himoyalangan edi, ya'ni cheklov umuman yo'q edi: bitta xodim (yoki
# o'g'irlangan token) skript bilan sekundiga o'nlab savol yuborsa, model
# navbatiga to'lib qolardi va BUTUN BANK uchun chat javob bermay qolardi.
#
# NEGA IP EMAS, USER_ID: bank ichida hamma bitta tashqi IP (NAT) ortida
# o'tiradi — IP bo'yicha cheklov bitta faol foydalanuvchi tufayli butun
# ofisni bloklab qo'yardi. `get_user_id_from_token` har bir xodimni alohida
# hisoblaydi.
#
# LIMIT: 20/daqiqa — tirik odam uchun bemalol yetadi (o'rtacha savol-javob
# 20-40 soniya), skript uchun esa sezilarli to'siq.
ASK_RATE_LIMIT = RateLimiter(times=20, minutes=1, identifier=get_user_id_from_token)

# Sarlavha yaratish ham LLM chaqiradi, lekin arzonroq (32 token) va har bir
# yangi suhbatda bir marta ishlaydi — limit bo'shroq.
TITLE_RATE_LIMIT = RateLimiter(times=30, minutes=1, identifier=get_user_id_from_token)


@router.post(
    "/title",
    response_model=GenerateTitleResult,
    dependencies=[Depends(TITLE_RATE_LIMIT)],
)
async def generate_title(
    data: GenerateTitleRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[GenerateTitleUseCase, Depends(get_generate_title_use_case)],
) -> GenerateTitleResult:
    """Birinchi xabar matnidan Qwen orqali qisqa suhbat sarlavhasi yasaydi."""
    return await use_case.execute(text=data.text)


# Keyingi savol takliflari — har javobdan keyin bitta qisqa chaqiruv
SUGGEST_RATE_LIMIT = RateLimiter(times=30, minutes=1, identifier=get_user_id_from_token)


@router.post(
    "/suggest",
    response_model=SuggestFollowupsResult,
    dependencies=[Depends(SUGGEST_RATE_LIMIT)],
)
async def suggest_followups(
    data: SuggestFollowupsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[SuggestFollowupsUseCase, Depends(get_suggest_followups_use_case)],
) -> SuggestFollowupsResult:
    """Javob tagidagi 3 ta "keyingi savol" taklifi (bo'sh ro'yxat ham bo'lishi mumkin)."""
    return await use_case.execute(data)


DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


@router.get("/sessions/{session_id}/export.docx")
async def export_session_docx(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[
        ExportSessionDocxUseCase, Depends(get_export_session_docx_use_case)
    ],
    lang: Annotated[str, Query(pattern="^(uz|uz_cyrl|ru)$")] = "uz",
) -> Response:
    """Suhbatni Word (.docx) faylga yuklab olish. PDF frontendda — brauzer
    chop etish oynasi orqali (kirill shriftlari bilan muammo bo'lmasin)."""
    result = await use_case.execute(
        user_id=current_user.id, session_id=session_id, lang=lang
    )
    # Kirill/lotin nom buzilmasin — RFC 5987 (filename*), eski mijozlarga ASCII
    ascii_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", result.filename[:-5]).strip("._")
    ascii_name = f"{ascii_stem if re.search(r'[A-Za-z0-9]', ascii_stem) else 'chat'}.docx"
    return Response(
        content=result.content,
        media_type=DOCX_MEDIA_TYPE,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_name}"; '
                f"filename*=UTF-8''{quote(result.filename)}"
            )
        },
    )


@router.get("/search", response_model=list[MessageSearchHit])
async def search_messages(
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[SearchMessagesUseCase, Depends(get_search_messages_use_case)],
    q: Annotated[str, Query(min_length=1, max_length=100)],
) -> list[MessageSearchHit]:
    """Chat tarixidan qidirish: xabar matni va suhbat sarlavhasi bo'yicha
    (lotin va kirill yozuvida). Faqat joriy foydalanuvchining suhbatlari."""
    return await use_case.execute(user_id=current_user.id, q=q)


@router.get("/sessions", response_model=list[SessionView])
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[ListSessionsUseCase, Depends(get_list_sessions_use_case)],
) -> list[SessionView]:
    """Joriy foydalanuvchining barcha suhbatlari."""
    return await use_case.execute(user_id=current_user.id)


@router.post("/sessions", status_code=201, response_model=SessionView)
async def create_session(
    current_user: Annotated[User, Depends(get_current_user)],
    data: CreateSessionModel,
    use_case: Annotated[CreateSessionUseCase, Depends(get_create_session_use_case)],
) -> SessionView:
    """Yangi suhbat yaratish."""
    return await use_case.execute(user_id=current_user.id, title=data.title)


@router.get("/sessions/{session_id}", response_model=SessionDetailView)
async def get_session_detail(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[GetSessionUseCase, Depends(get_get_session_use_case)],
) -> SessionDetailView:
    """Bitta suhbat va uning xabarlari."""
    return await use_case.execute(user_id=current_user.id, session_id=session_id)


@router.patch("/sessions/{session_id}", response_model=SessionView)
async def rename_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    data: RenameSessionModel,
    use_case: Annotated[RenameSessionUseCase, Depends(get_rename_session_use_case)],
) -> SessionView:
    """Suhbat nomini o'zgartirish."""
    return await use_case.execute(
        user_id=current_user.id, session_id=session_id, title=data.title
    )


@router.patch("/sessions/{session_id}/pin", response_model=SessionView)
async def pin_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    data: PinSessionModel,
    use_case: Annotated[PinSessionUseCase, Depends(get_pin_session_use_case)],
) -> SessionView:
    """Suhbatni ro'yxat tepasiga qadash (pin) yoki qadamasdan qo'yish."""
    return await use_case.execute(
        user_id=current_user.id, session_id=session_id, is_pinned=data.is_pinned
    )


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def delete_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[DeleteSessionUseCase, Depends(get_delete_session_use_case)],
) -> SuccessResponse:
    """Suhbatni o'chirish (yumshoq)."""
    return await use_case.execute(user_id=current_user.id, session_id=session_id)


@router.post(
    "/sessions/{session_id}/messages", status_code=201, response_model=MessageView
)
async def add_message(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    data: AddMessageModel,
    use_case: Annotated[AddMessageUseCase, Depends(get_add_message_use_case)],
) -> MessageView:
    """Suhbatga xabar qo'shish (role: 'user' yoki 'assistant')."""
    return await use_case.execute(
        user_id=current_user.id, session_id=session_id, data=data
    )


@router.delete(
    "/sessions/{session_id}/messages/{message_id}", response_model=SuccessResponse
)
async def delete_message(
    session_id: UUID,
    message_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[DeleteMessageUseCase, Depends(get_delete_message_use_case)],
) -> SuccessResponse:
    """Xabarni o'chirish (masalan regenerate qilinganda eski javob o'chiriladi)."""
    return await use_case.execute(
        user_id=current_user.id, session_id=session_id, message_id=message_id
    )


@router.patch(
    "/sessions/{session_id}/messages/{message_id}/vote", response_model=MessageView
)
async def vote_message(
    session_id: UUID,
    message_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    data: VoteMessageModel,
    use_case: Annotated[VoteMessageUseCase, Depends(get_vote_message_use_case)],
) -> MessageView:
    """Xabarga baho berish (like/dislike): vote = 'up' | 'down' | null."""
    return await use_case.execute(
        user_id=current_user.id,
        session_id=session_id,
        message_id=message_id,
        vote=data.vote,
        reason=data.reason,
        comment=data.comment,
    )


async def _resolve_history(
    data: QuestionRequest,
    current_user: User,
    history_use_case: LoadHistoryUseCase,
) -> list[ChatTurn]:
    """Savol uchun suhbat tarixini beradi.

    `session_id` berilgan bo'lsa — tarix BAZADAN o'qiladi (mobil ilova shu
    yo'lni ishlatadi). Aks holda mijoz yuborgan `history` ishlatiladi (web).
    Tarixsiz "19" kabi qisqa savol mavzuga bog'lanmay, noto'g'ri yo'naltirilardi.
    """
    if data.session_id is None:
        return data.history
    return await history_use_case.execute(
        user_id=current_user.id,
        session_id=data.session_id,
        question=data.question,
    )


@router.post(
    "/ask",
    response_model=AnswerResult,
    dependencies=[Depends(ASK_RATE_LIMIT)],
)
async def ask(
    data: QuestionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    embedder: Annotated[OllamaEmbedder, Depends(get_embedder)],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
    ai_client: Annotated[BaseAIClient, Depends(get_ai_client)],
    history_use_case: Annotated[
        LoadHistoryUseCase, Depends(get_load_history_use_case)
    ],
    translator: Annotated[TranslatorUseCase, Depends(get_translator_use_case)],
) -> AnswerResult:
    """Xodim savoli -> Qdrant qidiruv -> Qwen javob (RAG).

    Tarjimon rejimi (/translate) yoqilgan sessiyada javobni tarjimon beradi."""
    step = await translator.prepare(current_user.id, data.session_id, data.question)
    if step is not None:
        return await translator.answer(step)

    use_case = AnswerQuestionUseCase(
        embedder=embedder, store=store, ai_client=ai_client
    )
    history = await _resolve_history(data, current_user, history_use_case)
    started = time.monotonic()
    result = await use_case.execute(question=data.question, history=history)
    # Mobil shu yo'ldan keladi — xavfli so'rov u yerda ham qayd etilsin
    if use_case.last_outcome == "flagged" and use_case.last_flag:
        await log_question(
            QuestionLogEntry(
                user_id=current_user.id,
                question=data.question,
                intent=use_case.last_flag,
                outcome="flagged",
                top_score=None,
                sources_count=0,
                completion_tokens=result.completion_tokens,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        )
        await notify_safety_flag(current_user.username, data.question, use_case.last_flag)
    # Veb-qidiruvdan javob — admin "bazaga qo'shish" uchun qayd etiladi
    elif use_case.last_outcome == "web":
        await log_question(
            QuestionLogEntry(
                user_id=current_user.id,
                question=data.question,
                intent=use_case.last_intent,
                outcome="web",
                top_score=use_case.last_top_score,
                sources_count=len(result.sources),
                completion_tokens=result.completion_tokens,
                duration_ms=int((time.monotonic() - started) * 1000),
                source_urls=[s.url for s in result.sources if s.url],
            )
        )
    return result


@router.post("/ask/stream", dependencies=[Depends(ASK_RATE_LIMIT)])
async def ask_stream(
    data: QuestionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    embedder: Annotated[OllamaEmbedder, Depends(get_embedder)],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
    ai_client: Annotated[BaseAIClient, Depends(get_ai_client)],
    history_use_case: Annotated[
        LoadHistoryUseCase, Depends(get_load_history_use_case)
    ],
    translator: Annotated[TranslatorUseCase, Depends(get_translator_use_case)],
    redis_client: Annotated[Redis, Depends(get_redis_client)],
) -> StreamingResponse:
    """Xuddi /ask kabi, lekin javobni token-token (SSE oqim) qaytaradi —
    frontend real vaqtda matn va token sonini ko'rsatishi uchun."""
    # Tarjimon holati ham, tarix ham oqim BOSHLANISHIDAN oldin olinadi: oqim
    # ichida xato chiqsa, klient allaqachon 200 olgan bo'lardi va sababini
    # bilmasdi.
    step = await translator.prepare(current_user.id, data.session_id, data.question)
    events: AsyncIterator[dict[str, Any]]
    answer_use_case: AnswerQuestionUseCase | None = None
    if step is not None:
        events = translator.stream(step)
    else:
        answer_use_case = AnswerQuestionUseCase(
            embedder=embedder, store=store, ai_client=ai_client
        )
        history = await _resolve_history(data, current_user, history_use_case)
        # Kesh qatlami: birinchi savol, xavfsiz niyatlar (qara: answer_cache.py)
        events = cached_answer_stream(
            answer_use_case, data.question, history, redis_client
        )

    async def event_stream() -> AsyncIterator[str]:
        # Xatoning O'ZI faqat log'ga tushadi.
        #
        # ILGARI klientga `str(exc)` yuborilardi. Bu xavfli: xom xato matni
        # ichida ichki xost nomi, port, Qdrant/Ollama manzili yoki DSN
        # bo'lagi bo'lishi mumkin — ya'ni ichki infratuzilma xaritasi
        # brauzer konsoliga chiqib ketardi.
        #
        # Foydalanuvchiga esa u baribir foydasiz edi: "ConnectionError:
        # [Errno 111]" xodimga hech narsa aytmaydi. Endi tushunarli
        # o'zbekcha matn boradi.
        error_payload = {
            "type": "error",
            "message": (
                "Javob olishda xatolik yuz berdi. Bir oz kutib, qayta "
                "urinib ko'ring."
            ),
        }
        started = time.monotonic()
        outcome = "answered"
        tokens = 0
        sources_count = 0
        web_urls: list[str] = []
        try:
            async for ev in events:
                if ev.get("type") == "done":
                    tokens = int(ev.get("completion_tokens") or 0)
                    sources_count = len(ev.get("sources") or [])
                    web_urls = [
                        str(s["url"])
                        for s in ev.get("sources") or []
                        if isinstance(s, dict) and s.get("kind") == "web" and s.get("url")
                    ]
                # Bosqich hodisalari faqat so'ragan mijozga (qara: with_status)
                if ev.get("type") == "status" and not data.with_status:
                    continue
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except InfrastructureException as exc:
            outcome = "error"
            # Kutilgan xato (Ollama o'chiq, model topilmadi, timeout) — BITTA
            # qator. Sabab xabarning o'zida ("Ollama modeli topilmadi: ...");
            # 80 qatorli httpx traceback'i hech narsa qo'shmasdi.
            logger.error("Javob oqimi uzildi: %s | %r", exc, data.question[:200])
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
        except Exception:  # noqa: BLE001 - oqim uzilsa, klientga xabar beramiz
            outcome = "error"
            # Kutilmagan xato — bu yerda traceback haqiqatan kerak
            logger.exception("Javob oqimi uzildi: %r", data.question[:200])
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
        # Savollar statistikasi — faqat bot javoblari (tarjima rejimi emas).
        # Foydalanuvchi "To'xtatish"ni bossa generator shu yergacha yetmaydi
        # va yozuv qo'shilmaydi: javob oxirigacha bo'lmagan.
        if answer_use_case is not None:
            # "no_info" (bazada topilmadi) yoki "blocked" (prompt-injection)
            if outcome != "error" and answer_use_case.last_outcome != "answered":
                outcome = answer_use_case.last_outcome
            await log_question(
                QuestionLogEntry(
                    user_id=current_user.id,
                    question=data.question,
                    intent=answer_use_case.last_intent,
                    outcome=outcome,
                    top_score=answer_use_case.last_top_score,
                    sources_count=sources_count,
                    completion_tokens=tokens,
                    duration_ms=int((time.monotonic() - started) * 1000),
                    source_urls=web_urls or None,
                )
            )
            # Xavfli so'rov yoki so'kinish — adminga xabar
            if outcome == "flagged" and answer_use_case.last_flag:
                await notify_safety_flag(
                    current_user.username, data.question, answer_use_case.last_flag
                )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/rates", response_model=RatesResult)
async def exchange_rates(
    current_user: Annotated[User, Depends(get_current_user)],
    store: Annotated[QdrantStore, Depends(get_vector_store)],
) -> RatesResult:
    """Joriy valyuta kurslari — strukturali ko'rinishda (kurs oynasi uchun).

    Ma'lumot kunlik `scrape_exchange_rates` vazifasi yozib qo'ygan payload'dan
    olinadi: alohida jadval yoki takroriy so'rov (scraping) kerak emas. Har bir
    qatorda `delta_*` maydonlari bor — kurs kechagiga nisbatan qancha o'zgargani.
    """
    payloads = await store.search_by_field("title", RATES_TITLE, limit=40)
    for payload in payloads:
        raw = payload.get("rates_json")
        if not raw:
            continue
        try:
            data = json.loads(str(raw))
        except json.JSONDecodeError:
            break
        return RatesResult(
            stamp=str(data.get("stamp", "")),
            channels=data.get("channels", []),
            source_url=str(payload.get("source_url", "")),
        )
    # Vazifa hali ishlamagan yoki eski (JSON'siz) yozuv turibdi.
    return RatesResult()
