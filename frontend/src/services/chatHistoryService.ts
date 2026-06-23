// Mock chat tarixi — suhbatlar va xabarlarni localStorage'da saqlaydi (backendsiz).
// Keyinchalik backend ulanganda fetch chaqiruvlariga almashtiriladi.

export interface ApiSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ApiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ApiSessionDetail extends ApiSession {
  messages: ApiMessage[];
}

const SKEY = "turon_chat_sessions";
const MKEY = "turon_chat_messages"; // { [sessionId]: ApiMessage[] }

// Sun'iy kechikish — interfeys "jonli" his qildirishi uchun
const delay = (ms = 150) => new Promise((r) => setTimeout(r, ms));

// Bugundan necha kun oldingi ISO sana (sidebar guruhlash uchun)
function daysAgo(days: number): string {
  return new Date(Date.now() - days * 24 * 3600 * 1000).toISOString();
}

// Boshlang'ich suhbatlar — useChatHistory ularni updated_at bo'yicha
// Today / Yesterday / Previous 7 Days guruhlariga ajratadi
const SEED: ApiSession[] = [
  { id: "c1", title: "", created_at: daysAgo(0), updated_at: daysAgo(0) },
  { id: "c2", title: "Mijozga kechikkan to‘lov xati", created_at: daysAgo(0), updated_at: daysAgo(0) },
  { id: "c3", title: "Ipoteka refinansirovkasi shartlari", created_at: daysAgo(1), updated_at: daysAgo(1) },
  { id: "c4", title: "KYC onboarding siyosati xulosasi", created_at: daysAgo(1), updated_at: daysAgo(1) },
  { id: "c5", title: "Karta nizosi javob shabloni", created_at: daysAgo(3), updated_at: daysAgo(3) },
  { id: "c6", title: "Korporativ depozit stavkalari", created_at: daysAgo(4), updated_at: daysAgo(4) },
  { id: "c7", title: "AML xavf belgilari ro‘yxati", created_at: daysAgo(5), updated_at: daysAgo(5) },
];

function readSessions(): ApiSession[] {
  const raw = localStorage.getItem(SKEY);
  if (!raw) {
    localStorage.setItem(SKEY, JSON.stringify(SEED));
    return [...SEED];
  }
  try {
    return JSON.parse(raw) as ApiSession[];
  } catch {
    return [...SEED];
  }
}

function writeSessions(s: ApiSession[]) {
  localStorage.setItem(SKEY, JSON.stringify(s));
}

function readMessages(): Record<string, ApiMessage[]> {
  const raw = localStorage.getItem(MKEY);
  if (!raw) return {};
  try {
    return JSON.parse(raw) as Record<string, ApiMessage[]>;
  } catch {
    return {};
  }
}

function writeMessages(m: Record<string, ApiMessage[]>) {
  localStorage.setItem(MKEY, JSON.stringify(m));
}

export async function listSessions(): Promise<ApiSession[]> {
  await delay();
  return readSessions();
}

export async function createSession(title = ""): Promise<ApiSession> {
  await delay();
  const sessions = readSessions();
  const now = new Date().toISOString();
  const s: ApiSession = { id: "s" + Date.now(), title, created_at: now, updated_at: now };
  writeSessions([s, ...sessions]);
  return s;
}

export async function getSession(id: string): Promise<ApiSessionDetail> {
  await delay();
  const s = readSessions().find((x) => x.id === id);
  if (!s) throw new Error("Suhbat topilmadi");
  const messages = readMessages()[id] ?? [];
  return { ...s, messages };
}

export async function renameSession(id: string, title: string): Promise<ApiSession> {
  await delay();
  const sessions = readSessions();
  const s = sessions.find((x) => x.id === id);
  if (!s) throw new Error("Suhbat topilmadi");
  s.title = title;
  s.updated_at = new Date().toISOString();
  writeSessions(sessions);
  return s;
}

export async function deleteSession(id: string): Promise<void> {
  await delay();
  writeSessions(readSessions().filter((x) => x.id !== id));
  const m = readMessages();
  delete m[id];
  writeMessages(m);
}

export async function addMessage(
  sessionId: string,
  role: "user" | "assistant",
  content: string
): Promise<ApiMessage> {
  await delay();
  const m = readMessages();
  const msg: ApiMessage = {
    id: "m" + Date.now() + Math.random().toString(36).slice(2, 6),
    role,
    content,
    created_at: new Date().toISOString(),
  };
  m[sessionId] = [...(m[sessionId] ?? []), msg];
  writeMessages(m);
  // Suhbat updated_at yangilanadi — keyingi yuklashda "Today" guruhiga chiqadi
  const sessions = readSessions();
  const s = sessions.find((x) => x.id === sessionId);
  if (s) {
    s.updated_at = new Date().toISOString();
    writeSessions(sessions);
  }
  return msg;
}
