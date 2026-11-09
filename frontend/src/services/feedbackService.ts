// Yoqmagan javoblar navbati — /v1/admin/disliked-answers.
// Foydalanuvchi dislike bosgan bot javoblari: savol, javob, manba va sabab.

import { apiFetch } from "./authService";
import type { SourceRef, VoteReason } from "../types/chat";

export interface ApiDislikedAnswer {
  id: string;
  session_id: string;
  created_at: string;
  question?: string | null;
  answer: string;
  sources?: SourceRef[] | null;
  reason?: VoteReason | null;
  comment?: string | null;
  reviewed: boolean;
  user_name: string;
  username: string;
  session_title: string;
}

export interface ApiDislikedAnswerPage {
  items: ApiDislikedAnswer[];
  total: number;
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const data = await res.json();
    const d = data.detail ?? data.message;
    if (typeof d === "string") return d;
  } catch {
    /* JSON emas — umumiy xabar ko'rsatiladi */
  }
  return "";
}

export async function listDislikedAnswers(
  opts: { onlyOpen?: boolean; page?: number; size?: number } = {}
): Promise<ApiDislikedAnswerPage> {
  const q = new URLSearchParams();
  q.set("only_open", opts.onlyOpen === false ? "false" : "true");
  if (opts.page != null) q.set("page", String(opts.page));
  if (opts.size != null) q.set("size", String(opts.size));
  const res = await apiFetch(`/v1/admin/disliked-answers?${q.toString()}`);
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

// Javobni "ko'rib chiqildi" deb belgilash (reviewed=false — qayta ochish)
export async function reviewDislikedAnswer(id: string, reviewed: boolean): Promise<void> {
  const res = await apiFetch(`/v1/admin/disliked-answers/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ reviewed }),
  });
  if (!res.ok) throw new Error(await errorMessage(res));
}
