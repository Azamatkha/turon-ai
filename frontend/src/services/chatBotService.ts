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

// Haqiqiy javob: savol + oldingi suhbat (history) ni backend RAG endpointiga yuboradi
export async function askReply(
  question: string,
  history: ChatTurn[] = []
): Promise<string> {
  try {
    const res = await apiFetch("/v1/chat/ask", {
      method: "POST",
      body: JSON.stringify({ question, history }),
    });
    if (!res.ok) return FALLBACK;
    const data = await res.json();
    const answer = (data?.answer as string | undefined)?.trim();
    return answer || FALLBACK;
  } catch {
    return FALLBACK;
  }
}
