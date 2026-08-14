"""
Kredit / ipoteka / omonat hisob-kitobi — SOF funksiyalar (bazaga, tarmoqqa
murojaat yo'q).

NEGA BACKENDDA: ilgari bu formulalar frontendda (CalculatorModal.tsx va
utils/paymentSchedule.ts) yashardi. Bank shartlari o'zgarsa ikki joyni
(front + kelajakdagi har qanday integratsiya) yangilash kerak bo'lardi va
ular bir-biridan farq qilib ketishi mumkin edi. Endi formula YAGONA manbada.

NEGA `float`, `Decimal` EMAS: natijani JavaScript ham o'qiydi va u faqat
IEEE-754 double bilan ishlaydi. `Decimal` bilan hisoblasak, JSON ga
o'tkazishda baribir double ga yaxlitlanardi — ya'ni aniqlik yutug'i yo'q,
lekin kod og'irlashardi. Pul ko'rsatkichlari foydalanuvchiga baribir butun
so'mgacha yaxlitlanib chiqadi.
"""

from calendar import monthrange
from datetime import date

from src.calculator.schemas import (
    DepositResult,
    LoanResult,
    PayMethod,
    ScheduleResult,
    ScheduleRow,
)

# Sug'urta — asosiy qarzning shu ulushi. Rasmiy sayt shablonidan olingan:
# 1 000 000 -> 12 000 va 20 000 000 -> 240 000 (ikkalasi ham 1.2%).
INSURANCE_RATE = 0.012


def resolve_principal(
    amount: float | None,
    price: float | None,
    down_payment: float | None,
) -> float:
    """
    Kredit tanasi (principal) ni aniqlaydi.

    Ipoteka rejimida mijoz uy NARXINI va boshlang'ich to'lovni kiritadi —
    kredit esa ularning ayirmasi. Oddiy kredit/avtokreditda `amount` ning
    o'zi kredit tanasi bo'ladi.
    """
    if price is not None:
        return max(0.0, price - (down_payment or 0.0))
    return max(0.0, amount or 0.0)


def calc_loan(
    principal: float,
    rate_pct: float,
    months: int,
    method: PayMethod,
) -> LoanResult:
    """
    Kredit natijasi to'lov turiga qarab:

    * ``flat`` (ustama) — foiz butun summaga bir marta hisoblanadi, jami
      to'lov oylarga TENG bo'linadi. Har oy bir xil summa.
    * ``annuity`` — har oy teng to'lov, foiz esa qolgan qarzga hisoblanadi
      (boshida foiz ulushi katta, oxirida asosiy qarz ulushi katta).
    * ``diff`` (differensial) — asosiy qarz teng bo'linadi, foiz qoldiqqa
      hisoblanadi. Shuning uchun to'lov oydan oyga KAMAYIB boradi:
      birinchi oy eng katta, oxirgi oy eng kichik.
    """
    r = rate_pct / 100 / 12
    n = months or 1

    if method == "annuity":
        if r == 0:
            monthly = principal / n
        else:
            monthly = (principal * r * (1 + r) ** n) / ((1 + r) ** n - 1)
        first = last = monthly
        total_paid = monthly * n
    elif method == "diff":
        principal_part = principal / n
        first = principal_part + principal * r  # 1-oy: qarz to'liq
        last = principal_part + principal_part * r  # oxirgi oy: qarz eng kam
        total_paid = principal + r * principal * (n + 1) / 2
    else:  # flat
        interest = principal * (rate_pct / 100) * (n / 12)
        total_paid = principal + interest
        first = last = total_paid / n

    return LoanResult(
        principal=principal,
        first_payment=first,
        last_payment=last,
        total_paid=total_paid,
        overpay=total_paid - principal,
        # Differensialda to'lov har oy o'zgaradi — UI "1-oy / oxirgi oy"
        # ni alohida ko'rsatishi uchun shu bayroq kerak.
        varies=method == "diff",
    )


def calc_deposit(amount: float, rate_pct: float, months: int) -> DepositResult:
    """
    Omonat: oddiy (kapitallashuvsiz) foiz. Foyda = summa x stavka x yil ulushi.
    Kapitallashuv (foizga foiz) ataylab qo'shilmagan — bankdagi standart
    omonat shartlari shunday.
    """
    profit = amount * (rate_pct / 100) * (months / 12)
    return DepositResult(total=amount + profit, profit=profit)


def _add_months(start: date, months: int) -> date:
    """
    Sanaga oy qo'shadi, oy oxirini QIRQIB (clamp qilib): 31-yanvar + 1 oy =
    28/29-fevral.

    (JavaScript'ning `Date.setMonth` i bunday holatda keyingi oyga "oshib"
    ketardi — 31-yanvar + 1 oy = 3-mart. To'lov jadvali uchun bu noto'g'ri:
    to'lov kuni oydan oyga sakrab ketardi.)
    """
    total = start.month - 1 + months
    year = start.year + total // 12
    month = total % 12 + 1
    day = min(start.day, monthrange(year, month)[1])
    return date(year, month, day)


def build_schedule(
    principal: float,
    rate_pct: float,
    months: int,
    method: PayMethod,
    start_date: date,
) -> ScheduleResult:
    """
    Oylik to'lov jadvali (amortizatsiya).

    Har qator: to'lovdan OLDINGI qoldiq, asosiy qarz ulushi, foiz ulushi,
    jami to'lov va oldingi to'lovdan beri o'tgan kunlar. Oxirgi oyda
    qoldiq to'liq yopiladi — yaxlitlash qoldig'i osilib qolmaydi.
    """
    r = rate_pct / 100 / 12
    n = max(1, round(months))
    if r == 0:
        annuity_pay = principal / n
    else:
        annuity_pay = (principal * r * (1 + r) ** n) / ((1 + r) ** n - 1)
    # Ustama (flat): foiz butun summaga hisoblanadi, oylarga teng bo'linadi
    flat_interest_per = (principal * (rate_pct / 100) * (n / 12)) / n

    rows: list[ScheduleRow] = []
    balance = principal
    prev = start_date
    total_interest = 0.0

    for k in range(1, n + 1):
        pay_date = _add_months(start_date, k)
        days = (pay_date - prev).days
        bal = balance

        if method == "annuity":
            interest = bal * r
            principal_pay = annuity_pay - interest
        elif method == "diff":
            principal_pay = principal / n
            interest = bal * r
        else:  # flat
            principal_pay = principal / n
            interest = flat_interest_per

        # Oxirgi oy — qoldiqni to'liq yopamiz
        if k == n:
            principal_pay = bal

        total_interest += interest
        rows.append(
            ScheduleRow(
                k=k,
                date=pay_date,
                balance=bal,
                principal=principal_pay,
                interest=interest,
                total=principal_pay + interest,
                days=days,
            )
        )
        balance = bal - principal_pay
        prev = pay_date

    insurance = principal * INSURANCE_RATE
    total_paid = principal + total_interest
    return ScheduleResult(
        rows=rows,
        total_principal=principal,
        total_interest=total_interest,
        total_paid=total_paid,
        insurance=insurance,
        full_cost=total_paid + insurance,
    )
