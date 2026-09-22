// Xodimlar ma'lumotnomasi — ichki IP raqam qidiruvi (/v1/users/directory).
// Mobil ilova ham aynan shu endpointlardan foydalanadi.

import { apiFetch } from "./authService";

export interface DirectoryEntry {
  id: string;
  full_name: string;
  position: string | null;
  department: string | null;
  ip_number: string | null;
}

/** Xodimlari bor bo'limlar (alifbo tartibida) — 1-qadam: bo'lim tanlash. */
export async function fetchDirectoryDepartments(): Promise<string[]> {
  const res = await apiFetch("/v1/users/directory/departments");
  if (!res.ok) throw new Error(`directory departments: ${res.status}`);
  return (await res.json()) as string[];
}

/** Bo'lim xodimlari va/yoki ism/IP bo'yicha qidiruv (bo'lim yoki kamida 2 belgi shart). */
export async function searchDirectory(params: { department?: string; q?: string }): Promise<DirectoryEntry[]> {
  const qs = new URLSearchParams();
  if (params.department) qs.set("department", params.department);
  if (params.q) qs.set("q", params.q);
  const res = await apiFetch(`/v1/users/directory?${qs.toString()}`);
  if (!res.ok) throw new Error(`directory search: ${res.status}`);
  return (await res.json()) as DirectoryEntry[];
}
