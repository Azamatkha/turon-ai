// Bildirishnomalar xizmati — backendga ulangan (/v1/notifications).

import { apiFetch } from "./authService";

export interface ApiNotification {
  id: string;
  // "knowledge_updated" | "rates_updated" | "report_new"
  type: string;
  // Matnga qo'yiladigan qiymatlar, masalan { title: "Kredit siyosati" }
  params: Record<string, string>;
  is_read: boolean;
  created_at: string;
  entity_id?: string | null;
}

export interface ApiNotificationList {
  items: ApiNotification[];
  unread_count: number;
  total: number;
}

async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json();
    return data.detail || data.message || fallback;
  } catch {
    return fallback;
  }
}

export async function getUnreadCount(): Promise<number> {
  const res = await apiFetch("/v1/notifications/unread-count");
  if (!res.ok) throw new Error(await readError(res, "Bildirishnomalarni olishda xatolik"));
  const data = await res.json();
  return Number(data.count) || 0;
}

export async function listNotifications(
  opts: { limit?: number; offset?: number; onlyUnread?: boolean } = {}
): Promise<ApiNotificationList> {
  const q = new URLSearchParams();
  if (opts.limit != null) q.set("limit", String(opts.limit));
  if (opts.offset != null) q.set("offset", String(opts.offset));
  if (opts.onlyUnread) q.set("only_unread", "true");
  const qs = q.toString();
  const res = await apiFetch(`/v1/notifications${qs ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error(await readError(res, "Bildirishnomalarni olishda xatolik"));
  return res.json();
}

/** Real vaqtdagi oqim (SSE): server yangi bildirishnoma haqida signal beradi.
 *
 *  `EventSource` ishlatilmaydi — u Authorization sarlavhasini yubora olmaydi.
 *  Shuning uchun chat javoblaridagi kabi fetch + ReadableStream o'qiladi.
 *  Oqimda xabarning o'zi emas, faqat signal keladi — mazmunini chaqiruvchi
 *  odatdagi API orqali oladi. */
export async function streamNotifications(
  onSignal: () => void,
  signal: AbortSignal
): Promise<void> {
  const res = await apiFetch("/v1/notifications/stream", { signal });
  if (!res.ok || !res.body) throw new Error("Bildirishnoma oqimi ochilmadi");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      // ": ping" — ulanishni tirik ushlab turuvchi izoh, e'tiborsiz qoldiriladi
      if (chunk.startsWith("data:")) onSignal();
    }
  }
}

export async function markRead(id: string): Promise<void> {
  const res = await apiFetch(`/v1/notifications/${id}/read`, { method: "POST" });
  if (!res.ok) throw new Error(await readError(res, "Belgilashda xatolik"));
}

export async function markAllRead(): Promise<void> {
  const res = await apiFetch("/v1/notifications/read-all", { method: "POST" });
  if (!res.ok) throw new Error(await readError(res, "Belgilashda xatolik"));
}
