// Telegram yordam boti (aihelp) ma'lumotlari — bot o'zi backendga push qiladi,
// admin panel faqat o'qiydi (/v1/admin/telegram-bot).

import { apiFetch, readApiError } from "./authService";

export type TgDirection = "in" | "out";
// in: new | answered | closed;  out: sent | failed
export type TgStatus = "new" | "answered" | "closed" | "sent" | "failed";

export interface ApiTgUser {
  id: string;
  telegram_id: number;
  username: string;
  full_name: string;
  language: string;
  phone: string;
  reg_step: string;
  is_banned: boolean;
  first_seen_at: string;
  last_message_at: string | null;
  messages_count: number;
  pending_count: number;
}

export interface ApiTgMessage {
  id: string;
  direction: TgDirection;
  status: TgStatus;
  content_type: string;
  items: number;
  text: string;
  admin_name: string;
  sent_at: string;
  answered_at: string | null;
}

export interface TgUserPage {
  items: ApiTgUser[];
  total: number;
}

export interface TgMessagePage {
  user: ApiTgUser;
  items: ApiTgMessage[];
  total: number;
}

// Filtr: javob kutayotgan / ro'yxatdan o'tgan / o'tmagan / bloklangan
export type TgUserFilter = "" | "pending" | "registered" | "unregistered" | "banned";
// Saralash: botga kirgan vaqti (standart) yoki oxirgi murojaat
export type TgUserSort = "joined" | "last_message";

export async function listTgUsers(
  opts: { search?: string; page?: number; size?: number; status?: TgUserFilter; sort?: TgUserSort } = {}
): Promise<TgUserPage> {
  const q = new URLSearchParams();
  if (opts.search?.trim()) q.set("search", opts.search.trim());
  if (opts.status) q.set("status", opts.status);
  if (opts.sort) q.set("sort", opts.sort);
  if (opts.page != null) q.set("page", String(opts.page));
  if (opts.size != null) q.set("size", String(opts.size));
  const qs = q.toString();
  const res = await apiFetch(`/v1/admin/telegram-bot/users${qs ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error(await readApiError(res, "Telegram bot userlarini olishda xatolik"));
  return res.json();
}

export async function listTgMessages(
  userId: string,
  opts: { page?: number; size?: number } = {}
): Promise<TgMessagePage> {
  const q = new URLSearchParams();
  if (opts.page != null) q.set("page", String(opts.page));
  if (opts.size != null) q.set("size", String(opts.size));
  const qs = q.toString();
  const res = await apiFetch(
    `/v1/admin/telegram-bot/users/${encodeURIComponent(userId)}/messages${qs ? `?${qs}` : ""}`
  );
  if (!res.ok) throw new Error(await readApiError(res, "Yozishmalarni olishda xatolik"));
  return res.json();
}
