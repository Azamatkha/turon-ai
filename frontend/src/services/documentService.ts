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
