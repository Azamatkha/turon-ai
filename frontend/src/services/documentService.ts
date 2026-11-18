import { apiFetch } from "./authService";
import { readAnswerStream, type AskResult } from "./chatBotService";
import type { ThinkStep } from "../types/chat";

// Backend DOC_ANALYZE_MAX_BYTES bilan bir xil
export const DOC_MAX_BYTES = 9 * 1024 * 1024;

// Backend extractors.SUPPORTED_EXTS bilan bir xil
export const DOC_EXTS = [
  "pdf", "docx", "xlsx", "doc", "odt", "rtf", "xls", "ods", "ppt", "pptx", "odp",
  "jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff", "heic", "heif", "txt", "csv",
];
export const DOC_ACCEPT = DOC_EXTS.map((e) => "." + e).join(",");

export function docExt(name: string): string {
  const i = name.lastIndexOf(".");
  return i >= 0 ? name.slice(i + 1).toLowerCase() : "";
}

export function isSupportedDoc(name: string): boolean {
  return DOC_EXTS.includes(docExt(name));
}

// Backend aniq sabab bilan qaytargan xato (fayl buzilgan, tur qo'llanmaydi...) —
// foydalanuvchiga shu matn ko'rsatiladi
export class DocumentError extends Error {}

function currentLang(): string {
  try {
    const v = localStorage.getItem("turon-lang");
    return v === "uz_cyrl" || v === "ru" ? v : "uz";
  } catch {
    return "uz";
  }
}

// Hujjatni yuborib, tahlilni oqim (SSE) bilan oladi. Fayl serverda saqlanmaydi.
export async function analyzeDocumentStream(
  file: File,
  question: string,
  onDelta: (fullText: string, estTokens: number) => void,
  signal?: AbortSignal,
  onStatus?: (step: ThinkStep) => void
): Promise<AskResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("question", question);
  form.append("lang", currentLang());
  const res = await apiFetch("/v1/chat/analyze-document", { method: "POST", body: form, signal });
  if (!res.ok) {
    let detail = "";
    try {
      const data = (await res.json()) as { message?: unknown; detail?: unknown };
      detail = typeof data.message === "string" ? data.message : typeof data.detail === "string" ? data.detail : "";
    } catch {
      /* JSON emas */
    }
    throw new DocumentError(detail || `HTTP ${res.status}`);
  }
  try {
    return await readAnswerStream(res, onDelta, onStatus);
  } catch (e) {
    if (signal?.aborted) throw e;
    throw new DocumentError(e instanceof Error ? e.message : String(e));
  }
}

// Fayl yuborishdan OLDIN tekshiruv (backend ham tekshiradi — bu faqat tez javob)
export function validateDoc(file: File): "unsupported" | "tooLarge" | null {
  if (!isSupportedDoc(file.name)) return "unsupported";
  if (file.size > DOC_MAX_BYTES) return "tooLarge";
  return null;
}

// Chat tarixidagi hujjatli xabar: "📎 fayl.xlsx\nsavol" — kartochka bo'lib chiziladi
export const DOC_MSG_PREFIX = "📎 ";

export function docMessageText(fileName: string, question: string): string {
  return DOC_MSG_PREFIX + fileName + (question ? "\n" + question : "");
}

export function parseDocMessage(text: string): { name: string; question: string } | null {
  if (!text.startsWith(DOC_MSG_PREFIX)) return null;
  const rest = text.slice(DOC_MSG_PREFIX.length);
  const nl = rest.indexOf("\n");
  const name = (nl >= 0 ? rest.slice(0, nl) : rest).trim();
  // Fayl nomi kengaytmasiz bo'lsa — oddiy matn (foydalanuvchi o'zi 📎 yozgan)
  if (!name || !docExt(name)) return null;
  return { name, question: nl >= 0 ? rest.slice(nl + 1).trim() : "" };
}

// Kartochkadagi tur yorlig'i va rangi
export function docKind(name: string): { label: string; color: string } {
  const ext = docExt(name);
  if (ext === "pdf") return { label: "PDF", color: "#DC2626" };
  if (["doc", "docx", "odt", "rtf"].includes(ext)) return { label: ext.toUpperCase(), color: "#2563EB" };
  if (["xls", "xlsx", "ods", "csv"].includes(ext)) return { label: ext.toUpperCase(), color: "#16A34A" };
  if (["ppt", "pptx", "odp"].includes(ext)) return { label: ext.toUpperCase(), color: "#EA580C" };
  if (ext === "txt") return { label: "TXT", color: "#64748B" };
  return { label: ext.toUpperCase(), color: "#7C3AED" };
}
