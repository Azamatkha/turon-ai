// Bilim bazasi xizmati — admin yuklagan ma'lumotni backendga jo'natadi.
// Backend uni chunk'larga bo'lib, embed qilib, Qdrant vektorli bazaga yozadi.

import { apiFetch, readApiError } from "./authService";

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

// Hujjat turkumi — ADMIN o'zi yaratadi (backend: kb_categories jadvali).
// Avtomatik taxmin yo'q: turkum qo'yilmagan hujjat "Turkumsiz".
export interface KbCategory {
  key: string;
  name: string;
  // Savolda shu so'zlardan biri bo'lsa bot shu turkum ro'yxatini beradi
  keywords: string[];
  sort_order: number;
}

// Mijoz turi: jismoniy shaxslar / yuridik shaxslar / ikkalasi
export type Audience = "individual" | "legal" | "both";
export const AUDIENCES: Audience[] = ["individual", "legal", "both"];

export interface KbCategoryInput {
  name: string;
  keywords: string[];
  sort_order?: number | null;
}

// Ro'yxatda ko'rsatiladigan bitta yuklangan ma'lumot (sarlavha bo'yicha guruhlangan)
export interface KnowledgeItem {
  title: string;
  chunks: number;
  lang: string;
  preview: string;
  // Yuklangan vaqti (ISO). Eski yozuvlarda bo'lmasligi mumkin — bo'sh satr.
  uploaded_at?: string;
  // Amal qilish muddati "YYYY-MM-DD"; muddatsiz bo'lsa bo'sh satr
  valid_until?: string;
  // Matni aynan bir xil boshqa hujjatlar (dublikat)
  duplicates?: string[];
  // Admin qo'ygan turkumlar kalitlari (bir nechta bo'lishi mumkin); bo'sh — "Turkumsiz"
  categories?: string[];
  // Mijoz turi; belgilanmagan bo'lsa bo'sh satr
  audience?: Audience | "";
  // Admin izohi
  note?: string;
}

// Saytdan qayta tekshirish (backend/src/knowledge/rescrape.py)
export interface RescrapeStatus {
  enabled: boolean;
  running: boolean;
  last?: {
    started_at: string;
    finished_at: string;
    checked: number;
    unchanged: number;
    changed: string[];
    failed: { title: string; error: string }[];
  } | null;
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

const readError = readApiError;

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

// Amal qilish muddati: sana ("YYYY-MM-DD") yoki null — muddatsiz
export async function setKnowledgeValidity(title: string, validUntil: string | null): Promise<void> {
  const res = await apiFetch("/v1/admin/knowledge/validity", {
    method: "PATCH",
    body: JSON.stringify({ title, valid_until: validUntil }),
  });
  if (!res.ok) throw new Error(await readError(res, "Muddatni saqlashda xatolik"));
}

// Turkumlar (bo'sh — "Turkumsiz"), mijoz turi (null — belgilanmagan) va izoh
export async function setKnowledgeMeta(
  title: string,
  categories: string[],
  audience: Audience | null,
  note: string
): Promise<void> {
  const res = await apiFetch("/v1/admin/knowledge/meta", {
    method: "PATCH",
    body: JSON.stringify({ title, categories, audience, note: note.trim() || null }),
  });
  if (!res.ok) throw new Error(await readError(res, "Turkumni saqlashda xatolik"));
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

// Diagnostika: bazadagi xodim (doc_type=employee) nuqtalari haqida
export interface EmployeeStats {
  total_points: number;
  employee_count: number;
  departments: Record<string, number>;
  sample: {
    doc_type?: string;
    department?: string;
    fish?: string;
    ip?: string;
    phone?: string;
  } | null;
}

export async function employeeStats(): Promise<EmployeeStats> {
  const res = await apiFetch("/v1/admin/knowledge/employee-stats");
  if (!res.ok) throw new Error(await readError(res, "Tekshirishda xatolik"));
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

// PDF hujjat yuklash natijasi (backend nima qilganini ko'rsatish uchun)
export interface PdfUploadResult extends UploadResult {
  title: string;      // bazaga yozilgan sarlavha (bo'sh qoldirilsa AI aniqlaydi)
  pages: number;      // hujjatdagi sahifalar soni
  ocr_pages: number;  // shundan nechtasi skan bo'lib, OCR qilindi
  chars: number;      // tozalangandan keyingi matn uzunligi
}

// PDF yuklash FONDA bajariladi: server faylni qabul qilib darhol ish holatini
// qaytaradi, o'qish/tozalash/yozish fonda ketadi. Ilgari javob hujjat to'liq
// yozilgach kelardi va oraliq proxy (~60 s) so'rovni uzib qo'yardi — hujjat
// bazaga yozilsa ham "xatolik" ko'rinardi.
export type PdfJobStatus = "queued" | "running" | "done" | "failed";

export interface PdfJob {
  id: string;
  status: PdfJobStatus;
  filename: string;
  title: string;
  // reading (sahifalar) | cleaning (matn tozalash) | saving | ""
  stage: string;
  done: number;
  total: number;
  result: PdfUploadResult | null;
  error: string;
  created_at: string;
  updated_at: string;
}

export async function uploadPdf(file: File, title = ""): Promise<PdfJob> {
  const form = new FormData();
  form.append("file", file);
  form.append("title", title.trim());
  const res = await apiFetch("/v1/admin/knowledge/pdf", {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await readError(res, "PDF yuklashda xatolik"));
  return res.json();
}

export async function getPdfJob(id: string): Promise<PdfJob> {
  const res = await apiFetch(`/v1/admin/knowledge/pdf/jobs/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(await readError(res, "Yuklash holatini olishda xatolik"));
  return res.json();
}

export async function listPdfJobs(): Promise<PdfJob[]> {
  const res = await apiFetch("/v1/admin/knowledge/pdf/jobs");
  if (!res.ok) throw new Error(await readError(res, "Yuklashlar ro'yxatini olishda xatolik"));
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

export async function getRescrapeStatus(): Promise<RescrapeStatus> {
  const res = await apiFetch("/v1/admin/knowledge/rescrape");
  if (!res.ok) throw new Error(await readError(res, "Holatni olishda xatolik"));
  return res.json();
}

// Fon vazifasi navbatga qo'yiladi — natija bildirishnoma va holat orqali keladi
export async function runRescrape(): Promise<void> {
  const res = await apiFetch("/v1/admin/knowledge/rescrape", { method: "POST" });
  if (!res.ok) throw new Error(await readError(res, "Tekshiruvni boshlab bo'lmadi"));
}

// --- Turkumlar (admin boshqaradi) --- //

export async function listCategories(): Promise<KbCategory[]> {
  const res = await apiFetch("/v1/admin/knowledge/categories");
  if (!res.ok) throw new Error(await readError(res, "Turkumlarni olishda xatolik"));
  return res.json();
}

export async function createCategory(data: KbCategoryInput): Promise<KbCategory> {
  const res = await apiFetch("/v1/admin/knowledge/categories", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await readError(res, "Turkumni saqlashda xatolik"));
  return res.json();
}

export async function updateCategory(key: string, data: KbCategoryInput): Promise<KbCategory> {
  const res = await apiFetch(`/v1/admin/knowledge/categories/${encodeURIComponent(key)}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await readError(res, "Turkumni saqlashda xatolik"));
  return res.json();
}

export async function deleteCategory(key: string): Promise<void> {
  const res = await apiFetch(`/v1/admin/knowledge/categories/${encodeURIComponent(key)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await readError(res, "Turkumni o'chirishda xatolik"));
}

// Belgilangan hujjatlarga birdaniga: turkum qo'shish / olib tashlash (boshqa
// turkumlari saqlanadi) va mijoz turi ("none" — belgini olib tashlash)
export async function setKnowledgeBulk(
  titles: string[],
  change: { add?: string[]; remove?: string[]; audience?: Audience | "none" }
): Promise<void> {
  const res = await apiFetch("/v1/admin/knowledge/meta/bulk", {
    method: "PATCH",
    body: JSON.stringify({ titles, ...change }),
  });
  if (!res.ok) throw new Error(await readError(res, "Turkumni saqlashda xatolik"));
}

// Belgilangan hujjatlarni bittada o'chirish
export async function deleteKnowledgeBulk(titles: string[]): Promise<void> {
  const res = await apiFetch("/v1/admin/knowledge/bulk-delete", {
    method: "POST",
    body: JSON.stringify({ titles }),
  });
  if (!res.ok) throw new Error(await readError(res, "O'chirishda xatolik"));
}
