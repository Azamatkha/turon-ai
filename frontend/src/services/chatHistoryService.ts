// Haqiqiy chat tarixi xizmati — backendga ulangan (/v1/chat).

import { apiFetch, readApiError } from "./authService";
import type { SourceRef, VoteFeedback } from "../types/chat";
import { filenameFromDisposition } from "../utils/saveBlob";

export interface ApiSession {
  id: string;
  title: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

export interface ApiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  vote?: "up" | "down" | null;
  // Faqat assistant javobida; eski yozuvlarda null
  completion_tokens?: number | null;
  finish_reason?: string | null;
  sources?: SourceRef[] | null;
}

// Assistant javobi bilan birga saqlanadigan token statistikasi
export interface MessageStats {
  completionTokens: number;
  finishReason: string;
  sources?: SourceRef[];
}

export interface ApiSessionDetail extends ApiSession {
  messages: ApiMessage[];
}

const readError = readApiError;

// Chat tarixidan qidiruv (xabar matni + sarlavha, lotin va kirill yozuvida)
export interface MessageSearchHit {
  session_id: string;
  session_title: string;
  message_id: string;
  role: "user" | "assistant";
  snippet: string;
  created_at: string;
}

export async function searchMessages(q: string): Promise<MessageSearchHit[]> {
  const res = await apiFetch(`/v1/chat/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error(await readError(res, "Qidiruvda xatolik"));
  return res.json();
}

// Suhbatni Word (.docx) faylga eksport — fayl nomi serverdan (Content-Disposition)
export async function downloadSessionDocx(
  sessionId: string,
  lang: string
): Promise<{ blob: Blob; filename: string }> {
  const res = await apiFetch(
    `/v1/chat/sessions/${encodeURIComponent(sessionId)}/export.docx?lang=${encodeURIComponent(lang)}`
  );
  if (!res.ok) throw new Error(await readError(res, "Eksportda xatolik"));
  const filename = filenameFromDisposition(res.headers.get("content-disposition"), "Turon AI.docx");
  return { blob: await res.blob(), filename };
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

export async function pinSession(id: string, isPinned: boolean): Promise<ApiSession> {
  const res = await apiFetch(`/v1/chat/sessions/${id}/pin`, {
    method: "PATCH",
    body: JSON.stringify({ is_pinned: isPinned }),
  });
  if (!res.ok) throw new Error(await readError(res, "Pin qilishda xatolik"));
  return res.json();
}

export async function addMessage(
  sessionId: string,
  role: "user" | "assistant",
  content: string,
  stats?: MessageStats
): Promise<ApiMessage> {
  const res = await apiFetch(`/v1/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({
      role,
      content,
      ...(stats && {
        completion_tokens: stats.completionTokens,
        finish_reason: stats.finishReason || null,
        ...(stats.sources?.length && { sources: stats.sources }),
      }),
    }),
  });
  if (!res.ok) throw new Error(await readError(res, "Xabar qo'shishda xatolik"));
  return res.json();
}

// Birinchi xabar matnidan Qwen orqali qisqa suhbat sarlavhasi (ChatGPT uslubida)
export async function generateTitle(text: string): Promise<string> {
  const res = await apiFetch("/v1/chat/title", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(await readError(res, "Sarlavha yaratishda xatolik"));
  const data = await res.json();
  return (data?.title as string | undefined) ?? "";
}

export async function deleteMessage(sessionId: string, messageId: string): Promise<void> {
  const res = await apiFetch(`/v1/chat/sessions/${sessionId}/messages/${messageId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await readError(res, "Xabarni o'chirishda xatolik"));
}

export async function voteMessage(
  sessionId: string,
  messageId: string,
  vote: "up" | "down" | null,
  // Faqat dislike'da: sabab va ixtiyoriy izoh (admin ko'rib chiqadi)
  feedback?: VoteFeedback
): Promise<ApiMessage> {
  const res = await apiFetch(`/v1/chat/sessions/${sessionId}/messages/${messageId}/vote`, {
    method: "PATCH",
    body: JSON.stringify({
      vote,
      ...(vote === "down" && feedback && { reason: feedback.reason, comment: feedback.comment || null }),
    }),
  });
  if (!res.ok) throw new Error(await readError(res, "Baholashda xatolik"));
  return res.json();
}
