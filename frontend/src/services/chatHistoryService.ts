// Chat tarixi API'lari — suhbatlar va xabarlar (foydalanuvchiga bog'langan).
import { API_URL, authHeaders } from "./authService";

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

export async function listSessions(): Promise<ApiSession[]> {
  const res = await fetch(`${API_URL}/api/v1/chats`, { headers: authHeaders() });
  if (!res.ok) throw new Error("suhbatlar yuklanmadi");
  return (await res.json()) as ApiSession[];
}

export async function createSession(title = ""): Promise<ApiSession> {
  const res = await fetch(`${API_URL}/api/v1/chats`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("suhbat yaratilmadi");
  return (await res.json()) as ApiSession;
}

export async function getSession(id: string): Promise<ApiSessionDetail> {
  const res = await fetch(`${API_URL}/api/v1/chats/${id}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("suhbat topilmadi");
  return (await res.json()) as ApiSessionDetail;
}

export async function renameSession(id: string, title: string): Promise<ApiSession> {
  const res = await fetch(`${API_URL}/api/v1/chats/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("nomi o'zgartirilmadi");
  return (await res.json()) as ApiSession;
}

export async function deleteSession(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/chats/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("o'chirilmadi");
}

export async function addMessage(
  sessionId: string,
  role: "user" | "assistant",
  content: string
): Promise<ApiMessage> {
  const res = await fetch(`${API_URL}/api/v1/chats/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ role, content }),
  });
  if (!res.ok) throw new Error("xabar saqlanmadi");
  return (await res.json()) as ApiMessage;
}
