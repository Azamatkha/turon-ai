// Haqiqiy admin xizmati — backendga ulangan (/v1/users).

import { apiFetch, readApiError } from "./authService";

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
  phone_number?: string | null;
  ip_number?: string | null;
  // Admin qo'ygan kalit so'zlar (xodim nimaga mas'ul)
  keywords?: string[];
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
  // Kontaktlar: bo'sh satr — o'chirish
  phone_number?: string;
  ip_number?: string;
  // Kalit so'zlar: [] — hammasini o'chirish
  keywords?: string[];
}

const readError = readApiError;

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

export interface TopUserStat {
  name: string;
  username: string;
  department: string | null;
  count: number;
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
  // So'nggi 30 kunda eng ko'p savol bergan 5 xodim
  top_users?: TopUserStat[];
}

export async function getStats(): Promise<DashboardStats> {
  const res = await apiFetch("/v1/admin/stats");
  if (!res.ok) throw new Error(await readError(res, "Statistikani olishda xatolik"));
  return res.json();
}

// ---- Savollar tahlili — /v1/admin/questions ----

export interface QuestionStatItem {
  question: string;
  count: number;
  users: number;
  last_asked: string;
}

export interface QuestionAnalytics {
  days: number;
  summary: {
    total: number;
    no_info: number;
    errors: number;
    avg_duration_ms: number;
    total_tokens: number;
  };
  top: QuestionStatItem[];
  unanswered: QuestionStatItem[];
}

export async function getQuestionAnalytics(days = 30, limit = 20): Promise<QuestionAnalytics> {
  const res = await apiFetch(`/v1/admin/questions?days=${days}&limit=${limit}`);
  if (!res.ok) throw new Error(await readError(res, "Savollar tahlilini olishda xatolik"));
  return res.json();
}

// ---- Audit jurnali — /v1/admin/audit-logs ----

export interface AuditLogItem {
  id: string;
  created_at: string;
  actor_id?: string | null;
  actor_username: string;
  // "user.update", "knowledge.delete" ... (backend src/audit/actions.py)
  action: string;
  target_type: string;
  target_id?: string | null;
  target_label?: string | null;
  details?: Record<string, unknown> | null;
  ip?: string | null;
}

export interface AuditLogPage {
  items: AuditLogItem[];
  total: number;
}

export async function listAuditLogs(
  opts: { targetType?: string; search?: string; page?: number; size?: number } = {}
): Promise<AuditLogPage> {
  const q = new URLSearchParams();
  if (opts.targetType) q.set("target_type", opts.targetType);
  if (opts.search?.trim()) q.set("search", opts.search.trim());
  if (opts.page != null) q.set("page", String(opts.page));
  if (opts.size != null) q.set("size", String(opts.size));
  const qs = q.toString();
  const res = await apiFetch(`/v1/admin/audit-logs${qs ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error(await readError(res, "Audit jurnalini olishda xatolik"));
  return res.json();
}

// ---- Zaxira nusxalar — /v1/admin/backups ----

export type BackupKind = "postgres" | "qdrant";

export interface BackupKindStatus {
  kind: BackupKind;
  last_result?: "ok" | "fail" | null;
  last_run_at?: string | null;
  latest_at?: string | null;
  count: number;
  total_size: number;
}

export interface BackupOverview {
  keep_days: number;
  available: boolean;
  statuses: BackupKindStatus[];
  files: { kind: BackupKind; name: string; size: number; created_at: string }[];
}

export async function getBackups(): Promise<BackupOverview> {
  const res = await apiFetch("/v1/admin/backups");
  if (!res.ok) throw new Error(await readError(res, "Zaxira nusxalarni olishda xatolik"));
  return res.json();
}

// Bilim bazasi snapshot'ini hoziroq navbatga qo'yadi (Celery bajaradi)
export async function runQdrantBackup(): Promise<void> {
  const res = await apiFetch("/v1/admin/backups/qdrant", { method: "POST" });
  if (!res.ok) throw new Error(await readError(res, "Zaxira nusxani boshlashda xatolik"));
}

// ---- Tizim holati — /v1/admin/system ----

export interface SystemComponent {
  // "postgres" | "redis" | "qdrant" | "ollama" | "rabbitmq" | "celery"
  name: string;
  ok: boolean;
  latency_ms: number;
  critical: boolean;
  detail: string;
}

export interface SystemStatus {
  status: "ok" | "degraded" | "down";
  checked_at: string;
  components: SystemComponent[];
  llm: {
    hours: number;
    questions: number;
    errors: number;
    no_info: number;
    tokens: number;
    p50_ms: number;
    p95_ms: number;
    max_ms: number;
    hourly: { hour: string; questions: number; errors: number; no_info: number; avg_ms: number }[];
    // Javob keshi — bugun
    cache_hits_today: number;
    cache_misses_today: number;
  };
}

export async function getSystemStatus(): Promise<SystemStatus> {
  const res = await apiFetch("/v1/admin/system");
  if (!res.ok) throw new Error(await readError(res, "Tizim holatini olishda xatolik"));
  return res.json();
}
