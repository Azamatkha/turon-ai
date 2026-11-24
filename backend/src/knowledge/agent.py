"""Tool-calling agenti: model o'zi asbob tanlaydi.

Eski yo'lda savol yo'nalishini KOD tanlardi (kalit so'zlar + router niyati):
"xodim" so'zi uchrasa xodim qidiruvi ishga tushib ketardi, bitta savolda
ikki ish (foiz + hisob) bajarilmasdi. Bu yerda modelga asboblar ro'yxati
beriladi (agent_tools.TOOL_SPECS) — u kerakli asbob(lar)ni chaqiradi,
natijani ko'radi va javobni yozadi.

Sikl:
  1. chat_tools(messages, tools) — model yo matn yozadi, yo asbob chaqiradi;
  2. asboblar bajariladi, natija `role: tool` xabari bo'lib qaytadi;
  3. ko'pi bilan MAX_STEPS marta; oxirgi qadamda asbob berilmaydi — model
     javob yozishga majbur.

Har qanday xato (provayder tool-calling'ni qo'llamaydi, taym-aut, bo'sh
javob) — `answer` None bo'lib qoladi va chaqiruvchi ESKI yo'lga qaytadi."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from loggers import get_logger
from src.core.ai.interfaces import BaseAIClient
from src.knowledge.agent_tools import TOOL_SPECS, ToolContext, ToolResult, run_tool
from src.knowledge.context import source_refs
from src.knowledge.rates_scraper import RATES_TITLE
from src.knowledge.schemas import SourceRef

logger = get_logger(__name__)


@dataclass
class AgentAnswer:
    text: str
    sources: list[SourceRef] = field(default_factory=list)
    # Chaqirilgan asboblar (tartib bilan) — jurnal uchun
    tools: list[str] = field(default_factory=list)
    # Tekshiruvchi (verifier) javobni solishtiradigan faktlar
    context: str = ""
    tokens: int = 0
    finish_reason: str = "stop"
    # Javobni kod tuzgan (xodimlar / turkum ro'yxati) — tekshirilmaydi
    verbatim: bool = False
    # Asboblar hech narsa topmadi
    no_info: bool = False


def _found_nothing(r: ToolResult) -> bool:
    return r.text.startswith(("NOT FOUND", "ERROR", "NO SUCH CATEGORY"))


class ToolAgent:
    MAX_STEPS = 4
    # Bitta qadamda ko'pi bilan shuncha asbob (model "aylanib" qolmasin)
    MAX_CALLS_PER_STEP = 4
    # Barcha asbob natijalari jami (belgi, ~7500 token): system ~5500 +
    # asboblar ~900 + javob 2048 bilan eng kichik 16k oynaga ham sig'adi
    TOTAL_TOOL_CHARS = 24_000

    def __init__(
        self,
        ai_client: BaseAIClient,
        ctx: ToolContext,
        *,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> None:
        self.ai_client = ai_client
        self.ctx = ctx
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.temperature = temperature
        # Natija — run() tugagach o'qiladi. None: eski yo'lga qaytish kerak
        self.answer: AgentAnswer | None = None

    async def run(self, user_message: str) -> AsyncIterator[dict[str, Any]]:
        """`status` hodisalarini chiqaradi; natija `self.answer` da."""
        self.answer = None
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]
        tools: list[str] = []
        collected: list[tuple[str, ToolResult]] = []
        tokens = 0
        used = 0
        last_status: str | None = None

        for step in range(self.MAX_STEPS):
            last = step == self.MAX_STEPS - 1
            try:
                turn = await self.ai_client.chat_tools(
                    messages,
                    [] if last else TOOL_SPECS,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            except Exception as exc:  # noqa: BLE001 - har qanday xato: eski yo'l
                logger.warning("[Agent] chat_tools xatosi — eski yo'l: %s", exc)
                return
            tokens += turn.completion_tokens

            if not turn.tool_calls:
                text = turn.content.strip()
                if not text:
                    logger.warning("[Agent] bo'sh javob — eski yo'l")
                    return
                self.answer = self._finish(text, tools, collected, tokens)
                self.answer.finish_reason = turn.finish_reason or "stop"
                return

            messages.append({"role": "assistant", **turn.message})
            step_results: list[ToolResult] = []
            for call in turn.tool_calls[: self.MAX_CALLS_PER_STEP]:
                try:
                    res = await run_tool(self.ctx, call.name, call.arguments)
                except Exception as exc:  # noqa: BLE001 - bitta asbob butun javobni buzmasin
                    logger.warning("[Agent] %s asbobi xatosi: %s", call.name, exc)
                    res = ToolResult(text="ERROR: the tool failed, try another way.")
                if res.status != last_status:
                    yield {"type": "status", "step": res.status}
                    last_status = res.status
                logger.info(
                    "[Agent] %d-qadam: %s(%s) -> %d belgi%s",
                    step + 1, call.name, call.arguments, len(res.text),
                    " (tayyor)" if res.verbatim else "",
                )
                left = self.TOTAL_TOOL_CHARS - used
                content = res.text if len(res.text) <= left else (
                    res.text[: max(left, 0)] + "\n[TRUNCATED: answer from what is above]"
                )
                used += len(content)
                tools.append(call.name)
                collected.append((call.name, res))
                step_results.append(res)
                messages.append({"role": "tool", "tool_name": call.name, "content": content})

            # Birinchi qadamda faqat kod tuzgan javob(lar) — model qayta
            # yozmaydi (xodim ro'yxatini model kesib, raqam to'qigan edi)
            if step == 0 and step_results and all(r.verbatim for r in step_results):
                text = "\n\n".join(str(r.verbatim) for r in step_results)
                self.answer = self._finish(text, tools, collected, tokens)
                self.answer.verbatim = True
                return

    @staticmethod
    def _finish(
        text: str,
        tools: list[str],
        collected: list[tuple[str, ToolResult]],
        tokens: int,
    ) -> AgentAnswer:
        results: list[tuple[dict[str, Any], float]] = []
        for _, r in collected:
            results.extend(r.results)
        sources = source_refs(results)
        if any(r.status == "rates" and not _found_nothing(r) for _, r in collected):
            sources.append(SourceRef(title=RATES_TITLE, score=1.0))
        context = "\n\n".join(
            f"[{name}]\n{r.text}" for name, r in collected if not _found_nothing(r)
        )
        return AgentAnswer(
            text=text,
            sources=sources,
            tools=tools,
            context=context,
            tokens=tokens,
            no_info=bool(collected) and all(_found_nothing(r) for _, r in collected),
        )
