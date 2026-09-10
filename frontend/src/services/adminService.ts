// Haqiqiy admin xizmati — backendga ulangan (/v1/users).

import { apiFetch } from "./authService";

export type BackendRole = "admin" | "moderator" | "user";

export interface ApiUser {
  id: string;
  username: string;
  full_name: string;
  department: string | null;
  role: BackendRole;
  is_active: boolean;
  // Oxirgi 5 daqiqada faol bo'lganmi
  is_online: boolean;
  // Face-ID verifikatsiyasidan o'tganmi
  is_verified: boolean;
  // Verifikatsiya ma'lumotlari (tasdiqlanmagan/eski userlarda null)
  position?: string | null;
  branch?: string | null;
  pnfl?: string | null;
  patronym?: string | null;
  doc_seria?: string | null;
  doc_number?: string | null;
  birth_date?: string | null;
}

// Admin tomonidan tahrirlash — barcha maydonlar ixtiyoriy (faqat yuborilgani o'zgaradi).
// Verifikatsiya maydonlarida bo'sh satr = tozalash.
export interface AdminUserUpdate {
  username?: string;
  full_name?: string;
  department?: string;
  password?: string;
  is_verified?: boolean;
  pnfl?: string;
  patronym?: string;
  doc_seria?: string;
  doc_number?: string;
  birth_date?: string;
  position?: string;
  branch?: string;
}

async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json();
    return data.detail || data.message || fallback;
  } catch {
    return fallback;
  }
}

export async function listUsers(search = "", department = ""): Promise<ApiUser[]> {
  const params = new URLSearchParams();
  if (search.trim()) params.set("search", search.trim());
  if (department) params.set("department", department);
  const qs = params.toString();
  const res = await apiFetch(`/v1/users${qs ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error(await readError(res, "Foydalanuvchilarni olishda xatolik"));
  return res.json();
}

export async function createUser(input: {
  username: string;
  full_name: string;
  department?: string;
  password: string;
  role: BackendRole;
}): Promise<ApiUser> {
  const res = await apiFetch("/v1/users", {
    method: "POST",
    body: JSON.stringify({
      full_name: input.full_name,
      username: input.username,
      department: input.department ?? null,
      password: input.password,
      role: input.role,
    }),
  });
  if (!res.ok) throw new Error(await readError(res, "Bu login allaqachon band"));
  return res.json();
}

export async function changeRole(id: string, role: BackendRole): Promise<ApiUser> {
  const res = await apiFetch(`/v1/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
  if (!res.ok) throw new Error(await readError(res, "Rolni o'zgartirishda xatolik"));
  return res.json();
}

export async function updateUser(
  id: string,
  input: AdminUserUpdate
): Promise<ApiUser> {
  const res = await apiFetch(`/v1/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(await readError(res, "Foydalanuvchini yangilashda xatolik"));
  return res.json();
}

export async function deleteUser(id: string): Promise<void> {
  const res = await apiFetch(`/v1/users/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await readError(res, "Foydalanuvchini o'chirishda xatolik"));
}

// ── Dashboard statistikasi ──
export interface DeptStat {
  name: string;
  count: number;
  pct: number;
}

export interface WeeklyPoint {
  label: string;
  count: number;
}

export interface RecentActivityItem {
  name: string;
  action: string;
  when: string;
}

export interface DashboardStats {
  total_users: number;
  total_sessions: number;
  total_messages: number;
  total_departments: number;
  online: number;
  total_likes: number;
  total_dislikes: number;
  departments: DeptStat[];
  // Filtr uchun barcha foydalanuvchi bo'limlari (chatdan foydalanmaganlar ham)
  all_departments: string[];
  weekly: WeeklyPoint[];
  recent_activity: RecentActivityItem[];
}

export async function getStats(): Promise<DashboardStats> {
  const res = await apiFetch("/v1/admin/stats");
  if (!res.ok) throw new Error(await readError(res, "Statistikani olishda xatolik"));
  return res.json();
}
