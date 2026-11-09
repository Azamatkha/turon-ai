export type Role = "user" | "assistant";

// Backend oqimidagi bosqichlar ({"type":"status","step":...}) —
// backend/src/knowledge/usecases.py execute_stream bilan bir xil
export type ThinkStep = "analyze" | "rates" | "employees" | "search" | "write";
export const THINK_STEPS: readonly ThinkStep[] = ["analyze", "rates", "employees", "search", "write"];

// Javob tayangan bilim bazasi hujjati (backend SourceRef)
export interface SourceRef {
  title: string;
  score: number;
}

// Dislike sababi (backend VOTE_REASONS bilan bir xil)
export type VoteReason = "wrong" | "outdated" | "incomplete" | "other";
export interface VoteFeedback {
  reason: VoteReason;
  comment?: string;
}

export interface Msg {
  id: string;
  role: Role;
  text: string;
  time?: string; // ISO vaqt belgisi (yuborilgan/kelgan payt)
  vote?: "up" | "down" | null; // foydalanuvchi bahosi
  // Debug: token statistikasi (faqat assistant xabarlarida bo'ladi)
  debug?: { finishReason: string; completionTokens: number; maxTokens: number };
  // Javob oldidan "o'ylash": o'tgan bosqichlar va birinchi so'zgacha ketgan
  // vaqt (soniya). Faqat shu sessiyada — bazaga saqlanmaydi.
  thought?: { steps: ThinkStep[]; seconds: number };
  // Foydalanuvchi "To'xtatish"ni bosgan (bazada finish_reason="interrupted")
  interrupted?: boolean;
  // Javob qaysi hujjatlarga tayangani — javob tagida chip bo'lib ko'rinadi
  sources?: SourceRef[];
  // "Keyingi savol" takliflari — faqat shu sessiyada, bazaga saqlanmaydi
  suggestions?: string[];
}

export interface Chat {
  id: string;
  title: string;
  pinned: boolean;
  lastMessageAt: string; // ISO — oxirgi xabar/yangilanish vaqti (saralash va hover menyu uchun)
  messages: Msg[];
}

// ChatPage'da mavzu (light/dark) bo'yicha hisoblanadigan rang tokenlari
export interface ThemeTokens {
  bg: string;
  headBg: string;
  headBorder: string;
  strong: string;
  muted: string;
  card: string;
  /* Xabar bulutchasi — `card` dan SHAFFOFROQ. Alohida token, chunki menyu va
     kartochkalar shaffof bo'lsa ortidagi matn ko'rinib ketadi. */
  bubble: string;
  /* Foydalanuvchi xabarining bulutchasi — GRADIENT, tekis rang emas.
     Ilgari sidebar foni (`side.bg`) qayta ishlatilardi: dark rejimda u deyarli
     qora bo'lgani uchun xabar sahifadan "o'yiq" bo'lib ajralib turardi. */
  bubbleUser: string;
  cardBorder: string;
  input: string;
  disc: string;
  chipShadow: string;
}

export interface SideTokens {
  bg: string;
  fg: string;
  sub: string;
  active: string;
  border: string;
  logo: string;
  btn: string;
}
