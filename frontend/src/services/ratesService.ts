// Valyuta kurslari xizmati — backenddan strukturali kurslarni oladi
// (/v1/chat/rates). Ma'lumotni kunlik vazifa vektor bazaga yozib qo'yadi,
// shuning uchun bu so'rov yengil: saytga qayta murojaat qilinmaydi.

import { apiFetch } from "./authService";

export interface RateRow {
  code: string;
  name: string;
  buy: number | null;
  sell: number | null;
  cb: number | null;
  // Oldingi yangilanishga nisbatan o'zgarish. null — o'zgarmagan yoki
  // taqqoslash uchun ma'lumot yo'q (vazifa birinchi marta ishlaganda).
  delta_buy: number | null;
  delta_sell: number | null;
  delta_cb: number | null;
}

export interface RateChannel {
  key: string;
  label: string;
  rows: RateRow[];
}

export interface RatesResult {
  // "11.08.2026 11:10:00 dan ma'lumotlar"
  stamp: string;
  channels: RateChannel[];
  source_url: string;
}

export async function fetchRates(): Promise<RatesResult> {
  const res = await apiFetch("/v1/chat/rates");
  if (!res.ok) {
    throw new Error("rates_failed");
  }
  return (await res.json()) as RatesResult;
}
