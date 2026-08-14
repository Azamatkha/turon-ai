export type Role = "user" | "assistant";

export interface Msg {
  id: string;
  role: Role;
  text: string;
  time?: string; // ISO vaqt belgisi (yuborilgan/kelgan payt)
  vote?: "up" | "down" | null; // foydalanuvchi bahosi
  // Debug: token statistikasi (faqat assistant xabarlarida bo'ladi)
  debug?: { finishReason: string; completionTokens: number; maxTokens: number };
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
