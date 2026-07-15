// Bilim bazasi xizmati — admin yuklagan ma'lumotni backendga jo'natadi.
// Backend uni chunk'larga bo'lib, embed qilib, Qdrant vektorli bazaga yozadi.

import { apiFetch } from "./authService";

export interface UploadResult {
  // Bazaga yozilgan bo'laklar (chunk) soni — tasdiq uchun
  chunks: number;
}

// URL'ni ochib, toza matnini ajratib, bazaga yozadi
export async function scrapeUrl(url: string): Promise<UploadResult> {
  const res = await apiFetch("/v1/admin/knowledge/scrape", {
    method: "POST",
    body: JSON.stringify({ url: url.trim() }),
  });
  if (!res.ok) throw new Error(await readError(res, "Havoladan ma'lumot olishda xatolik"));
  return res.json();
}

// Ro'yxatda ko'rsatiladigan bitta yuklangan ma'lumot (sarlavha bo'yicha guruhlangan)
export interface KnowledgeItem {
  title: string;
  chunks: number;
  lang: string;
  preview: string;
}

export interface KnowledgeChunk {
  chunk_index: number;
  text: string;
}

// Bitta sarlavhaning to'liq tafsiloti (barcha bo'laklar)
export interface KnowledgeDetail {
  title: string;
  lang: string;
  chunks: KnowledgeChunk[];
}

async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json();
    return data.detail || data.message || fallback;
  } catch {
    return fallback;
  }
}

// Qo'lda kiritilgan matnni yuborish (faylsiz) — JSON
export async function uploadText(title: string, text: string): Promise<UploadResult> {
  const res = await apiFetch("/v1/admin/knowledge/upload", {
    method: "POST",
    body: JSON.stringify({ title: title.trim(), text: text.trim() }),
  });
  if (!res.ok) throw new Error(await readError(res, "Yuklashda xatolik"));
  return res.json();
}

// Yuklangan ma'lumotlar ro'yxati
export async function listKnowledge(): Promise<KnowledgeItem[]> {
  const res = await apiFetch("/v1/admin/knowledge");
  if (!res.ok) throw new Error(await readError(res, "Ma'lumotlarni olishda xatolik"));
  return res.json();
}

// Bitta sarlavhaning to'liq matni
export async function getKnowledgeDetail(title: string): Promise<KnowledgeDetail> {
  const res = await apiFetch(
    `/v1/admin/knowledge/detail?title=${encodeURIComponent(title)}`
  );
  if (!res.ok) throw new Error(await readError(res, "Ma'lumotni olishda xatolik"));
  return res.json();
}

// Ma'lumotni (sarlavha bo'yicha barcha bo'laklarni) o'chirish
export async function deleteKnowledge(title: string): Promise<void> {
  const res = await apiFetch(
    `/v1/admin/knowledge?title=${encodeURIComponent(title)}`,
    { method: "DELETE" }
  );
  if (!res.ok) throw new Error(await readError(res, "O'chirishda xatolik"));
}

// Ma'lumotni tahrirlash (eskisini o'chirib, yangi matnni qayta yozadi)
export async function updateKnowledge(
  oldTitle: string,
  title: string,
  text: string
): Promise<UploadResult> {
  const res = await apiFetch("/v1/admin/knowledge", {
    method: "PUT",
    body: JSON.stringify({ old_title: oldTitle, title: title.trim(), text: text.trim() }),
  });
  if (!res.ok) throw new Error(await readError(res, "Tahrirlashda xatolik"));
  return res.json();
}

// Xodimlar ma'lumotnomasi (Excel .xlsx) — har sheet bir bo'lim. Backend har
// xodimni alohida (doc_type=employee) Qdrant'ga yozadi. multipart/form-data.
export async function uploadEmployees(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiFetch("/v1/admin/knowledge/employees", {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await readError(res, "Xodimlar faylini yuklashda xatolik"));
  return res.json();
}

// Xodimlarni tayyor JSON ro'yxati orqali yozish (Excel'siz — backend rebuild
// shart emas). records: [{department, division, position, fish, ip, phone}, ...]
export async function uploadEmployeesJson(records: unknown[]): Promise<UploadResult> {
  const res = await apiFetch("/v1/admin/knowledge/employees-json", {
    method: "POST",
    body: JSON.stringify(records),
  });
  if (!res.ok) throw new Error(await readError(res, "Xodimlar (JSON) yuklashda xatolik"));
  return res.json();
}

// .docx faylni yuborish — multipart/form-data
export async function uploadFile(title: string, file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("title", title.trim());
  form.append("file", file);
  const res = await apiFetch("/v1/admin/knowledge/upload", {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await readError(res, "Yuklashda xatolik"));
  return res.json();
}
