import { apiFetch } from "./authService";
import { THINK_STEPS, type SourceRef, type ThinkStep } from "../types/chat";

// Xatolik yoki javob bo'lmaganda ko'rsatiladigan zaxira matn
const FALLBACK =
  "So‘rovingiz bo‘yicha javob topilmadi yoki serverda xatolik. 1234 raqamiga qo‘ng‘iroq qiling.";

// Eski stub (useChatSimulation hali ishlatadi) — zaxira matnni qaytaradi
export function pickReply(_t: string): string {
  return FALLBACK;
}

export interface ChatTurn {
  role: string; // "user" | "assistant"
  content: string;
}

export interface AskResult {
  text: string;
  // Debug: token statistikasi. finishReason === "length" bo'lsa, javob
  // token yetmagani sabab kesilib qolgan bo'lishi mumkin.
  finishReason: string;
  completionTokens: number;
  maxTokens: number;
  // Javob tayangan hujjatlar (umumiy savollarda bo'sh)
  sources: SourceRef[];
}

// Oqim (SSE) hodisasi — backend token-token yuboradigan bo'laklar
interface StreamEvent {
  type: "delta" | "done" | "error" | "status";
  text?: string;
  step?: string;
  completion_tokens?: number;
  finish_reason?: string;
  max_tokens?: number;
  message?: string;
  sources?: SourceRef[];
}

// Oqimli (streaming) javob: backend token-token yuboradi. `onDelta` har bir
// yangi bo'lakda joriy to'liq matn + taxminiy token soni bilan chaqiriladi.
// Xato bo'lsa (yoki brauzer stream'ni qo'llamasa) exception tashlaydi —
// chaqiruvchi tomon eski oqimsiz `askReply`ga qaytishi mumkin.
export async function askReplyStream(
  question: string,
  history: ChatTurn[] = [],
  onDelta: (fullText: string, estTokens: number) => void,
  signal?: AbortSignal,
  // Backend qaysi bosqichda ekani (savol tahlili, qidiruv, javob yozish...)
  onStatus?: (step: ThinkStep) => void
): Promise<AskResult> {
  const res = await apiFetch("/v1/chat/ask/stream", {
    method: "POST",
    body: JSON.stringify({ question, history, with_status: true }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error("stream unavailable");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let full = "";
  let completionTokens = 0;
  let finishReason = "";
  let maxTokens = 0;
  let sources: SourceRef[] = [];

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE hodisalari bo'sh qator (\n\n) bilan ajratiladi
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const jsonStr = line.slice(5).trim();
      if (!jsonStr) continue;
      let ev: StreamEvent;
      try {
        ev = JSON.parse(jsonStr) as StreamEvent;
      } catch {
        continue;
      }
      if (ev.type === "status") {
        // Notanish bosqich (backend yangiroq bo'lsa) — e'tiborsiz qoldiramiz
        const step = ev.step as ThinkStep;
        if (THINK_STEPS.includes(step)) onStatus?.(step);
      } else if (ev.type === "delta") {
        full += ev.text ?? "";
        // Aniq token faqat oxirida keladi — oraliqda taxminiy ko'rsatamiz
        onDelta(full, Math.max(1, Math.round(full.length / 4)));
      } else if (ev.type === "done") {
        completionTokens = ev.completion_tokens ?? 0;
        finishReason = ev.finish_reason ?? "";
        maxTokens = ev.max_tokens ?? 0;
        sources = Array.isArray(ev.sources) ? ev.sources : [];
      } else if (ev.type === "error") {
        throw new Error(ev.message ?? "stream error");
      }
    }
  }

  return { text: full || FALLBACK, finishReason, completionTokens, maxTokens, sources };
}

// Haqiqiy javob: savol + oldingi suhbat (history) ni backend RAG endpointiga yuboradi
export async function askReply(
  question: string,
  history: ChatTurn[] = []
): Promise<AskResult> {
  try {
    const res = await apiFetch("/v1/chat/ask", {
      method: "POST",
      body: JSON.stringify({ question, history }),
    });
    if (!res.ok) return { text: FALLBACK, finishReason: "", completionTokens: 0, maxTokens: 0, sources: [] };
    const data = await res.json();
    const answer = (data?.answer as string | undefined)?.trim();
    return {
      text: answer || FALLBACK,
      finishReason: (data?.finish_reason as string | undefined) ?? "",
      completionTokens: (data?.completion_tokens as number | undefined) ?? 0,
      maxTokens: (data?.max_tokens as number | undefined) ?? 0,
      sources: Array.isArray(data?.sources) ? (data.sources as SourceRef[]) : [],
    };
  } catch {
    return { text: FALLBACK, finishReason: "", completionTokens: 0, maxTokens: 0, sources: [] };
  }
}

// Javob tagidagi 3 ta "keyingi savol" taklifi. Ixtiyoriy: xato bo'lsa bo'sh
// ro'yxat (chat buzilmasin). Javob oqimidan keyin alohida so'raladi.
export async function suggestFollowups(
  question: string,
  answer: string,
  sources: string[] = []
): Promise<string[]> {
  try {
    const res = await apiFetch("/v1/chat/suggest", {
      method: "POST",
      body: JSON.stringify({ question, answer: answer.slice(0, 20000), sources: sources.slice(0, 10) }),
    });
    if (!res.ok) return [];
    const data = (await res.json()) as { suggestions?: unknown };
    return Array.isArray(data.suggestions)
      ? data.suggestions.filter((x): x is string => typeof x === "string").slice(0, 3)
      : [];
  } catch {
    return [];
  }
}

