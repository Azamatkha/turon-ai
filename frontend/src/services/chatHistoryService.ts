// Haqiqiy chat tarixi xizmati — backendga ulangan (/v1/chat).

import { apiFetch } from "./authService";

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

async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json();
    return data.detail || data.message || fallback;
  } catch {
    return fallback;
  }
}

export async function listSessions(): Promise<ApiSession[]> {
  const res = await apiFetch("/v1/chat/sessions");
  if (!res.ok) throw new Error(await readError(res, "Suhbatlarni olishda xatolik"));
  return res.json();
}

export async function createSession(title = ""): Promise<ApiSession> {
  const res = await apiFetch("/v1/chat/sessions", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(await readError(res, "Suhbat yaratishda xatolik"));
  return res.json();
}

export async function getSession(id: string): Promise<ApiSessionDetail> {
  const res = await apiFetch(`/v1/chat/sessions/${id}`);
  if (!res.ok) throw new Error(await readError(res, "Suhbat topilmadi"));
  return res.json();
}

export async function renameSession(id: string, title: string): Promise<ApiSession> {
  const res = await apiFetch(`/v1/chat/sessions/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(await readError(res, "Nomini o'zgartirishda xatolik"));
  return res.json();
}

export async function deleteSession(id: string): Promise<void> {
  const res = await apiFetch(`/v1/chat/sessions/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await readError(res, "Suhbatni o'chirishda xatolik"));
}

export async function addMessage(
  sessionId: string,
  role: "user" | "assistant",
  content: string
): Promise<ApiMessage> {
  const res = await apiFetch(`/v1/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({ role, content }),
  });
  if (!res.ok) throw new Error(await readError(res, "Xabar qo'shishda xatolik"));
  return res.json();
}
