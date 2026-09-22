// PDF konvertor — Word/Excel/PowerPoint hujjati yoki rasmlarni PDF'ga
// o'giradi (POST /v1/tools/convert/to-pdf). Mobil ilova ham shu endpointdan
// foydalanadi.

import { apiFetch } from "./authService";

// Backend bilan bir xil ro'yxat (src/tools/pdf_convert.py)
export const IMAGE_EXTS = ["jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff"];
export const OFFICE_EXTS = ["doc", "docx", "odt", "rtf", "xls", "xlsx", "ods", "ppt", "pptx", "odp"];
export const MAX_IMAGES = 20;
// Jami hajm (backend: config.app.CONVERT_MAX_BYTES)
export const CONVERT_MAX_BYTES = 9 * 1024 * 1024;

export const fileExt = (name: string): string => {
  const i = name.lastIndexOf(".");
  return i < 0 ? "" : name.slice(i + 1).toLowerCase();
};

/** Backend xato matni (bo'lmasa — null, UI o'z tarjimasini ko'rsatadi). */
async function readMessage(res: Response): Promise<string | null> {
  try {
    const data = await res.json();
    const msg = data?.message ?? data?.detail ?? data?.error?.message;
    return typeof msg === "string" ? msg : null;
  } catch {
    return null;
  }
}

export class ConvertError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

/** Fayl(lar)ni yuboradi va tayyor PDF'ni Blob ko'rinishida qaytaradi. */
export async function convertToPdf(files: File[]): Promise<Blob> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const res = await apiFetch("/v1/tools/convert/to-pdf", { method: "POST", body: form });
  if (!res.ok) throw new ConvertError(res.status, (await readMessage(res)) ?? "");
  return res.blob();
}
