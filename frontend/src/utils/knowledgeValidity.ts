// Bilim bazasi hujjatining amal qilish muddati holati.
// Backend bilan bir xil qoida (backend/src/knowledge/validity.py):
// `valid_until` — oxirgi amal qiladigan kun; ertasidan "muddati o'tgan".

export type ValidityState = "expired" | "soon" | "ok";

// Adminga "yaqinlashmoqda" deb ko'rsatiladigan oraliq (backend WARN_DAYS)
export const VALIDITY_WARN_DAYS = 7;

// Mahalliy sana "YYYY-MM-DD" ko'rinishida
export function todayIso(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function validityState(validUntil?: string | null): ValidityState | null {
  if (!validUntil) return null;
  const today = todayIso();
  if (validUntil < today) return "expired";
  const warn = new Date();
  warn.setDate(warn.getDate() + VALIDITY_WARN_DAYS);
  const pad = (n: number) => String(n).padStart(2, "0");
  const warnIso = `${warn.getFullYear()}-${pad(warn.getMonth() + 1)}-${pad(warn.getDate())}`;
  return validUntil <= warnIso ? "soon" : "ok";
}

// "2026-11-16" -> "16.11.2026"
export function fmtIsoDate(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return y && m && d ? `${d}.${m}.${y}` : iso;
}
