// Kalkulyator xizmati — kredit/omonat hisobi va to'lov jadvali BACKENDDAN
// keladi (/v1/calculator/*).
//
// NEGA: ilgari formulalar frontda (CalculatorModal.tsx + paymentSchedule.ts)
// takrorlangan edi. Bank shartlari o'zgarsa ikki joyni yangilash kerak
// bo'lardi. Endi formula yagona manbada — backend `src/calculator/services.py`.
// Frontda faqat ko'rsatish (formatlash) va Excel yig'ish qoldi.

import { apiFetch } from "./authService";

export type PayMethod = "flat" | "annuity" | "diff";

/** Kredit tanasi: oddiy kreditda `amount`, ipotekada `price` - `down_payment`. */
export interface LoanInput {
  amount?: number;
  price?: number;
  down_payment?: number;
  rate: number;
  months: number;
  method: PayMethod;
}

export interface LoanResult {
  principal: number;
  first_payment: number;
  last_payment: number;
  total_paid: number;
  overpay: number;
  /** faqat differensialda true — to'lov oydan oyga kamayadi */
  varies: boolean;
}

export interface DepositResult {
  total: number;
  profit: number;
}

export interface ScheduleRowDto {
  k: number;
  date: string; // ISO sana — "2026-08-14"
  balance: number;
  principal: number;
  interest: number;
  total: number;
  days: number;
}

export interface ScheduleResultDto {
  rows: ScheduleRowDto[];
  total_principal: number;
  total_interest: number;
  total_paid: number;
  insurance: number;
  full_cost: number;
}

async function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await apiFetch(path, {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    throw new Error(`calculator_failed_${res.status}`);
  }
  return (await res.json()) as T;
}

export function calcLoan(input: LoanInput, signal?: AbortSignal): Promise<LoanResult> {
  return post<LoanResult>("/v1/calculator/loan", input, signal);
}

export function calcDeposit(
  input: { amount: number; rate: number; months: number },
  signal?: AbortSignal
): Promise<DepositResult> {
  return post<DepositResult>("/v1/calculator/deposit", input, signal);
}

export function fetchSchedule(
  input: LoanInput,
  signal?: AbortSignal
): Promise<ScheduleResultDto> {
  return post<ScheduleResultDto>("/v1/calculator/schedule", input, signal);
}
