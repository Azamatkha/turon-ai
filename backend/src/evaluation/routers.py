"""Javob sifati sinov stendi — /v1/admin/eval.

─── SWAGGER'DA QANDAY TEKSHIRISH ───────────────────────────────────────────
1) POST /v1/admin/eval/cases  {"max_docs": 5}   -> 202 (savollar fonda tuziladi)
2) GET  /v1/admin/eval/status                   -> cases > 0 bo'lguncha kuting
3) POST /v1/admin/eval/runs                     -> o'lchov navbatga qo'yildi
4) GET  /v1/admin/eval/runs                     -> done/total, pass_rate
5) GET  /v1/admin/eval/runs/{id}?failed_only=true -> xato javoblar va izohlar
─────────────────────────────────────────────────────────────────────────────
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.evaluation.schemas import (
    EvalGenerateRequest,
    EvalRunDetail,
    EvalRunView,
    EvalStatusView,
)
from src.evaluation.usecases import (
    EvalStatusUseCase,
    GetEvalRunUseCase,
    ListEvalRunsUseCase,
    StartEvalGenerationUseCase,
    StartEvalRunUseCase,
    get_eval_run_use_case,
    get_eval_status_use_case,
    get_list_eval_runs_use_case,
    get_start_eval_generation_use_case,
    get_start_eval_run_use_case,
)
from src.user.auth.permissions.checker import require_permission
from src.user.auth.permissions.enum import Permission
from src.user.models import User

router = APIRouter()

AdminUser = Annotated[User, Depends(require_permission(Permission.EDIT_SETTINGS))]


@router.get("/status", response_model=EvalStatusView)
async def eval_status(
    current_user: AdminUser,
    use_case: Annotated[EvalStatusUseCase, Depends(get_eval_status_use_case)],
) -> EvalStatusView:
    """Savollar soni (uslub bo'yicha), tuzilish jarayoni va faol o'lchov."""
    return await use_case.execute()


@router.post("/cases", status_code=202)
async def generate_eval_cases(
    data: EvalGenerateRequest,
    current_user: AdminUser,
    use_case: Annotated[StartEvalGenerationUseCase, Depends(get_start_eval_generation_use_case)],
) -> None:
    """Bilim bazasidan sinov savollarini QAYTA tuzish (eski to'plam almashadi)."""
    await use_case.execute(data.max_docs)


@router.post("/runs", response_model=EvalRunView, status_code=202)
async def start_eval_run(
    current_user: AdminUser,
    use_case: Annotated[StartEvalRunUseCase, Depends(get_start_eval_run_use_case)],
) -> EvalRunView:
    """Yangi o'lchov: barcha savollar botdan o'tkaziladi va baholanadi."""
    return await use_case.execute(current_user.id)


@router.get("/runs", response_model=list[EvalRunView])
async def list_eval_runs(
    current_user: AdminUser,
    use_case: Annotated[ListEvalRunsUseCase, Depends(get_list_eval_runs_use_case)],
) -> list[EvalRunView]:
    return await use_case.execute()


@router.get("/runs/{run_id}", response_model=EvalRunDetail)
async def get_eval_run(
    run_id: UUID,
    current_user: AdminUser,
    use_case: Annotated[GetEvalRunUseCase, Depends(get_eval_run_use_case)],
    failed_only: Annotated[bool, Query()] = False,
) -> EvalRunDetail:
    return await use_case.execute(run_id, failed_only)
