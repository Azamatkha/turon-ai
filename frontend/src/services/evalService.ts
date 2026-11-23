// Javob sifati sinov stendi — /v1/admin/eval.
// Savollar bilim bazasidan bir marta tuziladi, har o'lchovda aynan shular
// botdan o'tkaziladi va asl hujjat bilan solishtiriladi.

import { apiFetch, readApiError } from "./authService";

export type EvalRunStatus = "queued" | "running" | "done" | "failed";

export interface EvalSummary {
  total: number;
  passed: number;
  pass_rate: number;
  by_failure: Record<string, number>;
  by_style: Record<string, { total: number; passed: number }>;
  verifier_missed: number;
  avg_latency_ms: number;
}

export interface EvalRun {
  id: string;
  status: EvalRunStatus;
  total: number;
  done: number;
  passed: number;
  pass_rate: number | null;
  prev_pass_rate: number | null;
  summary: EvalSummary | null;
  error: string;
  created_at: string;
  finished_at: string | null;
}

export interface EvalResult {
  id: string;
  doc_title: string;
  question: string;
  style: string;
  lang: string;
  expected: string[];
  answer: string;
  passed: boolean;
  failure: string;
  note: string;
  intent: string | null;
  outcome: string | null;
  pipeline_verdict: string | null;
  source_titles: string[];
  source_hit: boolean;
  latency_ms: number;
}

export interface EvalRunDetail extends EvalRun {
  results: EvalResult[];
}

export interface EvalStatus {
  cases: number;
  by_style: Record<string, number>;
  generating: boolean;
  active_run: EvalRun | null;
}

export async function getEvalStatus(): Promise<EvalStatus> {
  const res = await apiFetch("/v1/admin/eval/status");
  if (!res.ok) throw new Error(await readApiError(res, "Holatni olishda xatolik"));
  return res.json();
}

export async function generateEvalCases(maxDocs: number): Promise<void> {
  const res = await apiFetch("/v1/admin/eval/cases", {
    method: "POST",
    body: JSON.stringify({ max_docs: maxDocs }),
  });
  if (!res.ok) throw new Error(await readApiError(res, "Savollarni tuzib bo'lmadi"));
}

export async function startEvalRun(): Promise<EvalRun> {
  const res = await apiFetch("/v1/admin/eval/runs", { method: "POST" });
  if (!res.ok) throw new Error(await readApiError(res, "O'lchovni boshlab bo'lmadi"));
  return res.json();
}

export async function listEvalRuns(): Promise<EvalRun[]> {
  const res = await apiFetch("/v1/admin/eval/runs");
  if (!res.ok) throw new Error(await readApiError(res, "Ro'yxatni olishda xatolik"));
  return res.json();
}

export async function getEvalRun(id: string, failedOnly: boolean): Promise<EvalRunDetail> {
  const res = await apiFetch(
    `/v1/admin/eval/runs/${encodeURIComponent(id)}?failed_only=${failedOnly ? "true" : "false"}`,
  );
  if (!res.ok) throw new Error(await readApiError(res, "O'lchovni olishda xatolik"));
  return res.json();
}
