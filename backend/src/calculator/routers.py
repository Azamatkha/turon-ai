"""
Kalkulyator endpointlari — kredit/ipoteka oylik to'lovi, omonat foydasi va
to'lov jadvali.

Hisob-kitob SOF (bazaga yozmaydi, LLM chaqirmaydi), shuning uchun use-case
qatlami yo'q: router to'g'ridan-to'g'ri `services.py` dagi funksiyalarni
chaqiradi.

Nega token talab qilinadi: kalkulyator ichki bank ilovasining bir qismi,
ochiq internetga chiqarilmagan — qolgan /v1 endpointlari bilan bir xil
himoya darajasida turadi.

─── SWAGGER'DA QANDAY TEKSHIRISH ───────────────────────────────────────────
1) /v1/users/auth/login orqali access_token oling va "Authorize" ga kiriting.
2) POST /v1/calculator/loan
   {"amount": 50000000, "rate": 21.99, "months": 24, "method": "flat"}
   -> first_payment ~ 3 000 000, overpay ~ 21 990 000
3) POST /v1/calculator/deposit  {"amount": 10000000, "rate": 18, "months": 12}
   -> {"total": 11800000, "profit": 1800000}
4) POST /v1/calculator/schedule  (loan bilan bir xil body) -> 24 qator jadval
─────────────────────────────────────────────────────────────────────────────
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.calculator import services
from src.calculator.schemas import (
    DepositRequest,
    DepositResult,
    LoanRequest,
    LoanResult,
    ScheduleRequest,
    ScheduleResult,
)
from src.core.utils.datetime_utils import get_utc_now
from src.user.auth.dependencies import get_current_user
from src.user.models import User

router = APIRouter()


@router.post("/loan", response_model=LoanResult)
async def calculate_loan(
    data: LoanRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> LoanResult:
    """
    Kredit (yoki ipoteka) bo'yicha oylik to'lov, jami to'lov va ortiqcha
    to'lovni hisoblaydi.

    To'lov turlari: `flat` (ustama), `annuity` (teng to'lov),
    `diff` (differensial — to'lov kamayib boradi).
    """
    principal = services.resolve_principal(data.amount, data.price, data.down_payment)
    return services.calc_loan(principal, data.rate, data.months, data.method)


@router.post("/deposit", response_model=DepositResult)
async def calculate_deposit(
    data: DepositRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> DepositResult:
    """
    Omonat bo'yicha muddat oxiridagi summa va sof foydani hisoblaydi
    (oddiy foiz, kapitallashuvsiz).
    """
    return services.calc_deposit(data.amount, data.rate, data.months)


@router.post("/schedule", response_model=ScheduleResult)
async def payment_schedule(
    data: ScheduleRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ScheduleResult:
    """
    Oylik to'lov jadvalini (amortizatsiya) qaytaradi: har oy uchun qoldiq,
    asosiy qarz va foiz ulushi, jami to'lov; oxirida sug'urta va to'liq
    qiymat. Excel fayl mijoz tomonida shu qatorlardan yig'iladi.
    """
    principal = services.resolve_principal(data.amount, data.price, data.down_payment)
    start = data.start_date or get_utc_now().date()
    return services.build_schedule(
        principal, data.rate, data.months, data.method, start
    )
