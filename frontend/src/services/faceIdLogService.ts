// Face-ID loglari — /v1/admin/face-id-logs.
// `/auth/save` ga kelgan har bir GSI signature (xato bilan tugaganlari ham).

import { apiFetch } from "./authService";

export interface ApiFaceIdLog {
  id: string;
  created_at: string;
  // "ok" | "not_employee" | xato sababi
  result: string;
  // User topilmagan bo'lsa (masalan tokenda verificationId yo'q) — null
  username?: string | null;
  request_id?: string | null;
  // Kelgan xom JWT
  signature: string;
  // Decode qilingan claim'lar (`body` ochilgan holda)
  claims?: Record<string, unknown> | null;
  // --- signature ichidan ajratib olingan qisqa ma'lumot (tekshirilmagan) ---
  person_name?: string | null;
  pnfl?: string | null;
  document?: string | null;
  birth_date?: string | null;
  // signature ichida bizning accessToken bormi
  has_token: boolean;
  token_sub?: string | null;
  verification_id?: string | null;
}

export interface ApiFaceIdLogPage {
  items: ApiFaceIdLog[];
  total: number;
}

export async function listFaceIdLogs(
  opts: { onlyFailed?: boolean; page?: number; size?: number } = {}
): Promise<ApiFaceIdLogPage> {
  const q = new URLSearchParams();
  if (opts.onlyFailed) q.set("only_failed", "true");
  if (opts.page != null) q.set("page", String(opts.page));
  if (opts.size != null) q.set("size", String(opts.size));
  const qs = q.toString();
  const res = await apiFetch(`/v1/admin/face-id-logs${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    let message = "";
    try {
      const data = await res.json();
      const d = data.detail ?? data.message;
      if (typeof d === "string") message = d;
    } catch {
      /* JSON emas — umumiy xabar ko'rsatiladi */
    }
    throw new Error(message);
  }
  return res.json();
}
