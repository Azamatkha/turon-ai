import { apiFetch } from "./authService";

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
    if (!res.ok) return { text: FALLBACK, finishReason: "", completionTokens: 0, maxTokens: 0 };
    const data = await res.json();
    const answer = (data?.answer as string | undefined)?.trim();
    return {
      text: answer || FALLBACK,
      finishReason: (data?.finish_reason as string | undefined) ?? "",
      completionTokens: (data?.completion_tokens as number | undefined) ?? 0,
      maxTokens: (data?.max_tokens as number | undefined) ?? 0,
    };
  } catch {
    return { text: FALLBACK, finishReason: "", completionTokens: 0, maxTokens: 0 };
  }
}
