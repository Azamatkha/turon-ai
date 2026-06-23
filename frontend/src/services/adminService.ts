// Admin panel — foydalanuvchilarni boshqarish API'lari (faqat admin token bilan).
import { API_URL, authHeaders } from "./authService";

export type BackendRole = "admin" | "moderator" | "user";

export interface ApiUser {
  id: string;
  username: string;
  full_name: string;
  department: string | null;
  role: BackendRole;
  is_active: boolean;
}

export async function listUsers(search = "", department = ""): Promise<ApiUser[]> {
  const qs = new URLSearchParams();
  if (search) qs.set("search", search);
  if (department) qs.set("department", department);
  const res = await fetch(`${API_URL}/api/v1/admin/users?${qs.toString()}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("users yuklanmadi");
  const data = await res.json();
  return data.users as ApiUser[];
}

export async function createUser(input: {
  username: string;
  full_name: string;
  department?: string;
  password: string;
  role: BackendRole;
}): Promise<ApiUser> {
  const res = await fetch(`${API_URL}/api/v1/admin/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.message || "Foydalanuvchi qo'shilmadi");
  }
  return (await res.json()) as ApiUser;
}

export async function changeRole(id: string, role: BackendRole): Promise<ApiUser> {
  const res = await fetch(`${API_URL}/api/v1/admin/users/${id}/role`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ role }),
  });
  if (!res.ok) throw new Error("rol almashtirilmadi");
  return (await res.json()) as ApiUser;
}

export async function updateUser(
  id: string,
  input: { username?: string; full_name?: string; department?: string; password?: string }
): Promise<ApiUser> {
  const res = await fetch(`${API_URL}/api/v1/admin/users/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.message || "Foydalanuvchi yangilanmadi");
  }
  return (await res.json()) as ApiUser;
}

export async function deleteUser(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/admin/users/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("o'chirilmadi");
}
