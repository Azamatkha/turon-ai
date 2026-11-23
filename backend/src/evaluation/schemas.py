"""Stend ma'lumot tuzilmalari: ichki dataclass'lar (JSON'ga `asdict` bilan)
va admin API ko'rinishlari (pydantic)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from src.core.schemas import Base

# Savol uslublari. Bitta hujjat haqida turlicha so'rash — xodimlar aynan
# shunday yozadi: rasmiy, og'zaki, imlo xatolari bilan, ruscha, kirillcha.
# "absent" — hujjatda YO'Q narsa so'raladi: to'g'ri javob halol "topilmadi",
# raqam to'qish esa xato (to'qima javobni ushlash uchun).
STYLES: tuple[str, ...] = (
    "formal",
    "colloquial",
    "typo",
    "detail",
    "russian",
    "cyrillic",
    "absent",
)

# Xato turlari — har biri boshqa joyni tuzatishni bildiradi:
# misunderstood   — savol noto'g'ri tushunilgan (router/niyat)
# retrieval_miss  — ma'lumot bazada bor, lekin qidiruv topmadi
# not_found       — kerakli hujjat topilgan, lekin javobda yo'q deyilgan
# hallucination   — hujjatda yo'q yoki unga zid fakt
# incomplete      — javob to'g'ri yo'nalishda, lekin asosiy fakt tushib qolgan
# refused         — bank savolini rad etgan
# wrong_language  — savol tilida javob berilmagan
# error           — yo'l yiqildi (Ollama/timeout)
FAILURES: tuple[str, ...] = (
    "misunderstood",
    "retrieval_miss",
    "not_found",
    "hallucination",
    "incomplete",
    "refused",
    "wrong_language",
    "error",
)


@dataclass
class EvalCase:
    doc_title: str
    question: str
    style: str
    # Javob tili: uz | uz_cyrl | ru
    lang: str = "uz"
    # Javobda bo'lishi SHART bo'lgan qisqa faktlar ("26,9%", "60 oygacha")
    expected: list[str] = field(default_factory=list)


@dataclass
class CaseResult:
    case: EvalCase
    answer: str
    passed: bool
    # FAILURES'dan biri yoki "" (o'tdi)
    failure: str = ""
    # Hakamning o'zbekcha izohi — admin ko'radi
    note: str = ""
    intent: str | None = None
    outcome: str | None = None
    # Botning o'z tekshiruvchisi bergan baho (ok/fixed/failed/unchecked/None)
    pipeline_verdict: str | None = None
    source_titles: list[str] = field(default_factory=list)
    # Kerakli hujjat javob manbalari orasida bormi
    source_hit: bool = False
    latency_ms: int = 0


@dataclass
class StyleStat:
    total: int = 0
    passed: int = 0


@dataclass
class EvalSummary:
    total: int = 0
    passed: int = 0
    pass_rate: float = 0.0
    by_failure: dict[str, int] = field(default_factory=dict)
    by_style: dict[str, StyleStat] = field(default_factory=dict)
    # Botning tekshiruvchisi "ok" degan, hakam esa xato topgan — ichki
    # tekshiruvchi o'tkazib yuborgan xatolar soni
    verifier_missed: int = 0
    avg_latency_ms: int = 0


# ---- Admin API ko'rinishlari ----


class EvalRunView(Base):
    id: UUID
    status: str
    total: int
    done: int
    passed: int
    pass_rate: float | None = None
    # Oldingi tugagan o'lchov foizi — "avval/endi" farqi uchun
    prev_pass_rate: float | None = None
    summary: dict[str, Any] | None = None
    error: str = ""
    created_at: datetime
    finished_at: datetime | None = None


class EvalResultView(Base):
    id: UUID
    doc_title: str
    question: str
    style: str
    lang: str
    expected: list[str] = Field(default_factory=list)
    answer: str
    passed: bool
    failure: str
    note: str
    intent: str | None = None
    outcome: str | None = None
    pipeline_verdict: str | None = None
    source_titles: list[str] = Field(default_factory=list)
    source_hit: bool
    latency_ms: int


class EvalRunDetail(EvalRunView):
    results: list[EvalResultView] = Field(default_factory=list)


class EvalStatusView(Base):
    cases: int
    by_style: dict[str, int] = Field(default_factory=dict)
    generating: bool = False
    active_run: EvalRunView | None = None


class EvalGenerateRequest(Base):
    # Nechta hujjatdan savol tuzilsin (har biridan 7 ta). Ko'p hujjat — uzoq
    # o'lchov: 30 hujjat ≈ 210 savol ≈ 1.5–2 soat.
    max_docs: int = Field(default=30, ge=1, le=300)
