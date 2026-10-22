// EDO yo'riqnomalari (video) — ro'yxat, ko'rish va admin yuklashi.
//
// Video BO'LAKLAB yuklanadi: nginx har bir so'rovni 10 MB bilan cheklaydi,
// video esa 200 MB gacha. Fayl 8 MB lik bo'laklarga bo'linib ketma-ket
// yuboriladi (backend: src/guides/storage.py).

import { API_URL, apiFetch } from "./authService";

export interface EdoGuide {
  id: string;
  title: string;
  size_bytes: number;
  // Qisqa muddatli imzoli havola (token ichida) — <video src> uchun
  video_url: string;
  created_at: string;
}

interface UploadStart {
  upload_id: string;
  chunk_size: number;
  max_bytes: number;
}

async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json();
    return data.detail || data.message || fallback;
  } catch {
    return fallback;
  }
}

export async function listGuides(): Promise<EdoGuide[]> {
  const res = await apiFetch("/v1/guides");
  if (!res.ok) throw new Error(await readError(res, "Yo'riqnomalarni yuklab bo'lmadi"));
  return res.json();
}

// Backend nisbiy yo'l qaytaradi — API manzili bilan to'liq havolaga aylantiramiz
export function guideVideoSrc(guide: EdoGuide): string {
  return `${API_URL}${guide.video_url}`;
}

// Videoni bo'laklab yuklab, yo'riqnoma yaratadi. `onProgress` — 0..1.
// `signal` bekor qilinsa, serverdagi yarim yuklash ham o'chiriladi.
export async function uploadGuide(
  file: File,
  title: string,
  onProgress: (fraction: number) => void,
  signal?: AbortSignal,
): Promise<EdoGuide> {
  const startRes = await apiFetch("/v1/admin/guides/uploads", { method: "POST", signal });
  if (!startRes.ok) throw new Error(await readError(startRes, "Yuklashni boshlab bo'lmadi"));
  const start: UploadStart = await startRes.json();

  if (file.size > start.max_bytes) {
    await cancelUpload(start.upload_id);
    throw new Error("Fayl hajmi juda katta");
  }

  try {
    let offset = 0;
    while (offset < file.size) {
      const chunk = file.slice(offset, offset + start.chunk_size);
      const res = await apiFetch(`/v1/admin/guides/uploads/${start.upload_id}?offset=${offset}`, {
        method: "PUT",
        body: chunk,
        headers: { "Content-Type": "application/octet-stream" },
        signal,
      });
      if (!res.ok) throw new Error(await readError(res, "Videoni yuklashda xatolik"));
      const { received } = (await res.json()) as { received: number };
      offset = received;
      onProgress(offset / file.size);
    }

    const res = await apiFetch("/v1/admin/guides", {
      method: "POST",
      body: JSON.stringify({ upload_id: start.upload_id, title: title.trim() }),
      signal,
    });
    if (!res.ok) throw new Error(await readError(res, "Yo'riqnomani saqlab bo'lmadi"));
    return res.json();
  } catch (e) {
    // Xato yoki bekor qilish — serverda yarim fayl qolmasin
    void cancelUpload(start.upload_id);
    throw e;
  }
}

async function cancelUpload(uploadId: string): Promise<void> {
  try {
    await apiFetch(`/v1/admin/guides/uploads/${uploadId}`, { method: "DELETE" });
  } catch {
    /* tashlab ketilgan fayl serverda 24 soatda baribir tozalanadi */
  }
}

export async function renameGuide(id: string, title: string): Promise<EdoGuide> {
  const res = await apiFetch(`/v1/admin/guides/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ title: title.trim() }),
  });
  if (!res.ok) throw new Error(await readError(res, "Nomini o'zgartirib bo'lmadi"));
  return res.json();
}

export async function deleteGuide(id: string): Promise<void> {
  const res = await apiFetch(`/v1/admin/guides/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await readError(res, "O'chirib bo'lmadi"));
}
