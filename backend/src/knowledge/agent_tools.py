"""Tool-calling agenti uchun asboblar.

Har asbob — mavjud kodga YUPQA qobiq: qidiruv, katalog, kurslar, xodimlar va
kalkulyator `AnswerQuestionUseCase` / `calculator.services` dagi funksiyalarni
chaqiradi. Yangi biznes mantiq bu yerda yozilmaydi.

Ikki xil natija bor:
* oddiy (`text`) — model ko'radigan FAKTLAR; yakuniy javobni model yozadi;
* tayyor (`verbatim`) — javobni KOD tuzgan (xodimlar ro'yxati, turkum
  mahsulotlari ro'yxati). Model uni qayta yozmaydi: ilgari xodim
  ro'yxatini modelga berganda u ro'yxatni kesib, soxta raqam to'qigan."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from loggers import get_logger
from src.calculator.services import calc_deposit, calc_loan, resolve_principal
from src.core.utils.uzbek_script import to_cyrillic, to_latin
from src.knowledge.answer_helpers import (
    _fmt_amount,
    _format_employee_answer,
    _norm_apostrophes,
    _rates_calculation,
)
from src.knowledge.context import context_blocks

if TYPE_CHECKING:
    from src.knowledge.usecases import AnswerQuestionUseCase

logger = get_logger(__name__)

# Bitta asbob natijasining eng ko'p hajmi (belgi) — bir nechta asbob
# chaqirilsa ham prompt oynaga sig'sin
TOOL_RESULT_MAX_CHARS = 9600
# Kalkulyator chegaralari (calculator/schemas.py dagi UI chegaralari bilan bir xil)
_MAX_MONTHS = 360
_MAX_RATE = 200.0
_MAX_AMOUNT = 100_000_000_000.0


@dataclass
class ToolResult:
    text: str
    # SSE "status" qadami (frontend "qidiryapman..." kabi yozadi)
    status: str = "search"
    # Kod tuzgan tayyor javob — model qayta yozmaydi
    verbatim: str | None = None
    # Manbalar (search_knowledge topgan bo'laklar)
    results: list[tuple[dict[str, Any], float]] = field(default_factory=list)


@dataclass
class ToolContext:
    uc: "AnswerQuestionUseCase"
    want_cyrillic: bool = False


Handler = Callable[[ToolContext, dict[str, Any]], Awaitable[ToolResult]]


def _str(args: dict[str, Any], key: str) -> str:
    return " ".join(str(args.get(key) or "").split())


def _num(args: dict[str, Any], key: str) -> float | None:
    raw = args.get(key)
    if raw is None or raw == "":
        return None
    try:
        return float(str(raw).replace(" ", "").replace(",", "."))
    except ValueError:
        return None


class ToolArgError(ValueError):
    """Model asbobga noto'g'ri argument berdi — matni modelga qaytariladi."""


# ----- asboblar ----- #


async def search_knowledge(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    query = _str(args, "query")
    if not query:
        raise ToolArgError("query is required")
    uc = ctx.uc
    q = to_latin(query)
    results, lexical = await uc._search_chunks(q, q)
    top = results[0][1] if results else 0.0
    if not results or (top < uc.MIN_SCORE and not lexical):
        return ToolResult(text="NOT FOUND: the bank database has nothing on this query.")
    return ToolResult(
        text=context_blocks(results, TOOL_RESULT_MAX_CHARS),
        results=results,
    )


async def list_products(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    category = _str(args, "category")
    if not category:
        raise ToolArgError("category is required")
    reply, only_title = await ctx.uc._broad_category_reply(category, ctx.want_cyrillic)
    if reply is not None:
        return ToolResult(text=reply, verbatim=reply)
    if only_title:
        # Turkum emas, bitta aniq mahsulot — uning hujjatini beramiz
        results = await ctx.uc._results_by_title(only_title)
        if results:
            return ToolResult(
                text=context_blocks(results, TOOL_RESULT_MAX_CHARS), results=results
            )
    return ToolResult(
        text="NO SUCH CATEGORY in the catalog. Use search_knowledge instead."
    )


async def get_exchange_rates(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    uc = ctx.uc
    data = await uc._load_rates()
    if data is None:
        return ToolResult(text="NOT FOUND: exchange rates are not loaded.", status="rates")
    request = _str(args, "request")
    q = _norm_apostrophes(to_latin(request).lower())
    codes, channels = uc._rates_wanted(q)
    table = uc._rates_table(data, codes, channels) or uc._rates_table(data, set(), set())
    calc = _rates_calculation(q, data, codes, channels)
    text = f"{calc}\n\n{table}" if calc else table
    return ToolResult(text=text[:TOOL_RESULT_MAX_CHARS], status="rates")


async def find_employee(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    query = to_latin(_str(args, "query"))
    if not query:
        raise ToolArgError("query is required")
    uc = ctx.uc
    emps = await uc._directory_hits(query)
    note: str | None = None
    if not emps:
        route = await uc._employee_route(query)
        if route is not None and route[0] == "answer":
            emps, note = route[1], uc._emp_note
    if not emps:
        return ToolResult(
            text="NOT FOUND: no employee matches this query.", status="employees"
        )
    text = _format_employee_answer(emps, query, note)
    if ctx.want_cyrillic:
        text = to_cyrillic(text)
    return ToolResult(text=text, verbatim=text, status="employees")


_METHOD_NAMES = {
    "flat": "teng (ustama)",
    "annuity": "annuitet",
    "diff": "differensial",
}


def _check_calc(amount: float | None, rate: float | None, months: float | None) -> int:
    if amount is None or rate is None or months is None:
        raise ToolArgError("amount, rate and months are required numbers")
    if not 0 < amount <= _MAX_AMOUNT:
        raise ToolArgError("amount is out of range")
    if not 0 <= rate <= _MAX_RATE:
        raise ToolArgError("rate is out of range (percent per year)")
    if not 1 <= months <= _MAX_MONTHS:
        raise ToolArgError("months must be between 1 and 360")
    return int(round(months))


async def calculate_loan(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    price = _num(args, "price")
    principal = resolve_principal(_num(args, "amount"), price, _num(args, "down_payment"))
    months = _check_calc(principal or None, _num(args, "rate"), _num(args, "months"))
    rate = float(_num(args, "rate") or 0.0)
    method = str(args.get("method") or "annuity")
    if method not in _METHOD_NAMES:
        method = "annuity"
    r = calc_loan(principal, rate, months, method)  # type: ignore[arg-type]
    lines = [
        "CALCULATION (computed by the bank calculator — use these numbers as is):",
        f"* Kredit summasi: {_fmt_amount(principal, 0)} so'm",
        f"* Foiz: yillik {rate:g}%, muddat: {months} oy, to'lov turi: {_METHOD_NAMES[method]}",
    ]
    if r.varies:
        lines.append(f"* Birinchi oy to'lovi: {_fmt_amount(r.first_payment, 0)} so'm")
        lines.append(f"* Oxirgi oy to'lovi: {_fmt_amount(r.last_payment, 0)} so'm")
    else:
        lines.append(f"* Oylik to'lov: {_fmt_amount(r.first_payment, 0)} so'm")
    lines.append(f"* Jami to'lov: {_fmt_amount(r.total_paid, 0)} so'm")
    lines.append(f"* Ortiqcha to'lov (foiz): {_fmt_amount(r.overpay, 0)} so'm")
    lines.append("NOTE: this is an estimate; real terms depend on the product.")
    return ToolResult(text="\n".join(lines), status="calc")


async def calculate_deposit(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    amount = _num(args, "amount")
    months = _check_calc(amount, _num(args, "rate"), _num(args, "months"))
    rate = float(_num(args, "rate") or 0.0)
    r = calc_deposit(float(amount or 0.0), rate, months)
    lines = [
        "CALCULATION (computed by the bank calculator — use these numbers as is):",
        f"* Omonat summasi: {_fmt_amount(float(amount or 0.0), 0)} so'm",
        f"* Foiz: yillik {rate:g}%, muddat: {months} oy (kapitallashuvsiz)",
        f"* Foyda: {_fmt_amount(r.profit, 0)} so'm",
        f"* Muddat oxirida jami: {_fmt_amount(r.total, 0)} so'm",
        "NOTE: this is an estimate; real terms depend on the deposit product.",
    ]
    return ToolResult(text="\n".join(lines), status="calc")


# ----- ro'yxat (Ollama `tools` formati) ----- #


def _fn(name: str, description: str, props: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


TOOL_SPECS: list[dict[str, Any]] = [
    _fn(
        "search_knowledge",
        "Search the bank's knowledge base (products, tariffs, internal rules, orders, "
        "procedures, uploaded documents). Use for ANY question about the bank's facts. "
        "Call several times with different queries if the question has several parts.",
        {"query": {"type": "string", "description": "Standalone search query in Uzbek (Latin)"}},
        ["query"],
    ),
    _fn(
        "list_products",
        "List ALL products of one category from the catalog (e.g. 'kreditlar', "
        "'omonatlar', 'kartalar', 'filiallar'). Use only when the user asks what "
        "products/types exist in a category, not about one product.",
        {"category": {"type": "string", "description": "Category as the user named it"}},
        ["category"],
    ),
    _fn(
        "get_exchange_rates",
        "Current currency exchange rates of the bank; can also convert an amount.",
        {"request": {"type": "string", "description": "e.g. '120 dollar so'mda', 'yevro kursi'"}},
        ["request"],
    ),
    _fn(
        "find_employee",
        "Find a bank EMPLOYEE's phone / internal number (IP) / department by name, "
        "internal number, department or responsibility. Only when the user wants to "
        "contact or identify a person — NOT for rules about employees.",
        {"query": {"type": "string", "description": "Name, internal number or department"}},
        ["query"],
    ),
    _fn(
        "calculate_loan",
        "Compute loan payments (monthly payment, total, overpayment). Never compute "
        "loan numbers yourself — always call this. For a mortgage give price and "
        "down_payment instead of amount.",
        {
            "amount": {"type": "number", "description": "Loan amount in so'm"},
            "price": {"type": "number", "description": "Property price (mortgage)"},
            "down_payment": {"type": "number", "description": "Down payment in so'm"},
            "rate": {"type": "number", "description": "Annual interest rate, percent"},
            "months": {"type": "integer", "description": "Term in months"},
            "method": {
                "type": "string",
                "enum": ["annuity", "diff", "flat"],
                "description": "Payment type; default annuity",
            },
        },
        ["rate", "months"],
    ),
    _fn(
        "calculate_deposit",
        "Compute deposit profit (simple interest). Never compute it yourself.",
        {
            "amount": {"type": "number", "description": "Deposit amount in so'm"},
            "rate": {"type": "number", "description": "Annual interest rate, percent"},
            "months": {"type": "integer", "description": "Term in months"},
        },
        ["amount", "rate", "months"],
    ),
]

HANDLERS: dict[str, Handler] = {
    "search_knowledge": search_knowledge,
    "list_products": list_products,
    "get_exchange_rates": get_exchange_rates,
    "find_employee": find_employee,
    "calculate_loan": calculate_loan,
    "calculate_deposit": calculate_deposit,
}


async def run_tool(ctx: ToolContext, name: str, args: dict[str, Any]) -> ToolResult:
    """Asbobni bajaradi. Noma'lum asbob yoki noto'g'ri argument — xato matni
    natija sifatida qaytadi (model tuzatib qayta chaqirishi mumkin)."""
    handler = HANDLERS.get(name)
    if handler is None:
        return ToolResult(text=f"ERROR: unknown tool {name!r}")
    try:
        return await handler(ctx, args)
    except ToolArgError as exc:
        return ToolResult(text=f"ERROR: {exc}")
