// Murojaatlar (muammo / taklif) xizmati — /v1/reports va /v1/admin/reports.

import { apiFetch } from "./authService";

export type ReportKind = "problem" | "suggestion";
export type ReportStatus = "new" | "in_progress" | "resolved";

export interface ApiReport {
  id: string;
  kind: ReportKind;
  title: string;
  description: string;
  status: ReportStatus;
  has_screenshot: boolean;
  created_at: string;
}

export interface ApiReportAdmin extends ApiReport {
  user_name: string;
  user_department?: string | null;
  admin_comment: string;
  resolved_at?: string | null;
}

export interface ApiReportPage {
  items: ApiReportAdmin[];
  total: number;
  new_count: number;
}

async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json();
    const d = data.detail ?? data.message;
    if (Array.isArray(d)) {
      return d.map((e) => e?.msg || e?.message || String(e)).join("; ") || fallback;
    }
    if (typeof d === "string") return d;
    return fallback;
  } catch {
    return fallback;
  }
}

export async function createReport(
  kind: ReportKind,
  title: string,
  description: string,
  screenshot?: File | null
): Promise<ApiReport> {
  const form = new FormData();
  form.append("kind", kind);
  form.append("title", title);
  form.append("description", description);
  if (screenshot) form.append("screenshot", screenshot);
  const res = await apiFetch("/v1/reports", { method: "POST", body: form });
  if (!res.ok) throw new Error(await readError(res, "Yuborishda xatolik"));
  return res.json();
}

export async function listReports(
  opts: { status?: ReportStatus | ""; page?: number; size?: number } = {}
): Promise<ApiReportPage> {
  const q = new URLSearchParams();
  if (opts.status) q.set("status", opts.status);
  if (opts.page != null) q.set("page", String(opts.page));
  if (opts.size != null) q.set("size", String(opts.size));
  const qs = q.toString();
  const res = await apiFetch(`/v1/admin/reports${qs ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error(await readError(res, "Murojaatlarni olishda xatolik"));
  return res.json();
}

export async function getReport(id: string): Promise<ApiReportAdmin> {
  const res = await apiFetch(`/v1/admin/reports/${id}`);
  if (!res.ok) throw new Error(await readError(res, "Murojaat topilmadi"));
  return res.json();
}

export async function updateReport(
  id: string,
  status: ReportStatus,
  adminComment: string
): Promise<ApiReportAdmin> {
  const res = await apiFetch(`/v1/admin/reports/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status, admin_comment: adminComment }),
  });
  if (!res.ok) throw new Error(await readError(res, "Saqlashda xatolik"));
  return res.json();
}

/** Skrinshotni himoyalangan endpointdan blob sifatida oladi.
 *  Fayl ochiq URL'da turmagani uchun <img src> ga to'g'ridan-to'g'ri
 *  qo'yib bo'lmaydi — object URL yasaymiz (foydalanuvchi uni revoke qilsin). */
export async function fetchReportScreenshot(id: string): Promise<string> {
  const res = await apiFetch(`/v1/admin/reports/${id}/screenshot`);
  if (!res.ok) throw new Error(await readError(res, "Skrinshotni olishda xatolik"));
  return URL.createObjectURL(await res.blob());
}
