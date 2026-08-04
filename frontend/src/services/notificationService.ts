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

export async function markRead(id: string): Promise<void> {
  const res = await apiFetch(`/v1/notifications/${id}/read`, { method: "POST" });
  if (!res.ok) throw new Error(await readError(res, "Belgilashda xatolik"));
}

export async function markAllRead(): Promise<void> {
  const res = await apiFetch("/v1/notifications/read-all", { method: "POST" });
  if (!res.ok) throw new Error(await readError(res, "Belgilashda xatolik"));
}
