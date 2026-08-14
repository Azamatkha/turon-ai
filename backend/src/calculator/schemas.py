"""Kalkulyator so'rov/javob sxemalari."""

# `date` ATAYLAB taxallus bilan import qilinadi: `ScheduleRow` da `date` nomli
# MAYDON bor, ya'ni `date: date` yozilsa nom o'zini-o'zi soya qilib qolardi
# (Python 3.14 dagi kechiktirilgan annotatsiyalar bilan bu xatoga olib keladi).
from datetime import date as DateType
from typing import Literal, Self

from pydantic import Field, model_validator

from src.core.schemas import Base

PayMethod = Literal["flat", "annuity", "diff"]

# Chegara qiymatlar UI slayderlari bilan bir xil. Validatsiya baribir kerak:
# API to'g'ridan-to'g'ri ham chaqirilishi mumkin, UI esa yagona himoya emas.
MAX_MONTHS = 360
MAX_RATE = 200.0
MAX_AMOUNT = 100_000_000_000.0


class LoanRequest(Base):
    """
    Kredit/ipoteka so'rovi.

    Kredit tanasi ikki xil beriladi:
      * oddiy kredit/avtokredit — `amount` (kredit summasi);
      * ipoteka — `price` (uy narxi) + `down_payment` (boshlang'ich to'lov),
        kredit tanasi ularning ayirmasi bo'ladi.
    """

    amount: float | None = Field(default=None, ge=0, le=MAX_AMOUNT)
    price: float | None = Field(default=None, ge=0, le=MAX_AMOUNT)
    down_payment: float | None = Field(default=None, ge=0, le=MAX_AMOUNT)
    rate: float = Field(ge=0, le=MAX_RATE, description="Yillik foiz stavkasi")
    months: int = Field(ge=1, le=MAX_MONTHS, description="Muddat (oy)")
    method: PayMethod = "flat"

    @model_validator(mode="after")
    def _require_amount_or_price(self) -> Self:
        if self.amount is None and self.price is None:
            raise ValueError("amount yoki price dan kamida bittasi kerak")
        return self


class LoanResult(Base):
    principal: float = Field(description="Kredit tanasi (ipotekada: narx - boshlang'ich)")
    first_payment: float = Field(description="Birinchi oy to'lovi")
    last_payment: float = Field(description="Oxirgi oy to'lovi (flat/annuitetda first bilan bir xil)")
    total_paid: float = Field(description="Butun muddat davomida jami to'lov")
    overpay: float = Field(description="Ortiqcha to'lov = jami to'lov - kredit tanasi")
    varies: bool = Field(description="To'lov oydan oyga o'zgaradimi (faqat differensialda true)")


class DepositRequest(Base):
    amount: float = Field(ge=0, le=MAX_AMOUNT, description="Omonat summasi")
    rate: float = Field(ge=0, le=MAX_RATE, description="Yillik foiz stavkasi")
    months: int = Field(ge=1, le=MAX_MONTHS, description="Muddat (oy)")


class DepositResult(Base):
    total: float = Field(description="Muddat oxirida qo'lga tegadigan summa")
    profit: float = Field(description="Sof foyda (foiz daromadi)")


class ScheduleRequest(LoanRequest):
    start_date: DateType | None = Field(
        default=None,
        description="Jadval boshlanish sanasi. Berilmasa — bugungi sana.",
    )


class ScheduleRow(Base):
    k: int = Field(description="To'lov tartib raqami")
    date: DateType = Field(description="To'lov sanasi")
    balance: float = Field(description="Shu to'lovdan OLDINGI kredit qoldig'i")
    principal: float = Field(description="Asosiy qarzni so'ndirish ulushi")
    interest: float = Field(description="Foizlar ulushi")
    total: float = Field(description="Shu oy jami to'lov")
    days: int = Field(description="Oldingi to'lovdan beri o'tgan kunlar")


class ScheduleResult(Base):
    rows: list[ScheduleRow]
    total_principal: float
    total_interest: float
    total_paid: float
    insurance: float = Field(description="Sug'urta — kredit tanasining 1.2% i")
    full_cost: float = Field(description="To'liq qiymat = jami to'lov + sug'urta")
