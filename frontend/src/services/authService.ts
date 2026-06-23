// Backend bilan oddiy autentifikatsiya (register/login/logout/me) + token boshqaruvi.
export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "turon_token";
const ROLE_KEY = "turon_role";

export interface Me {
  id: string;
  username: string;
  email: string;
  full_name: string;
  department: string | null;
  role: string;
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRole(): string | null {
  return localStorage.getItem(ROLE_KEY);
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function store(token: string, role: string) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(ROLE_KEY, role);
}

export async function login(loginValue: string, password: string): Promise<string> {
  const res = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login: loginValue, password }),
  });
  if (!res.ok) throw new Error("Login yoki parol noto'g'ri");
  const data = await res.json();
  store(data.access_token, data.role ?? "user");
  return data.access_token as string;
}

export async function register(input: {
  username: string;
  full_name: string;
  department?: string;
  password: string;
}): Promise<string> {
  const res = await fetch(`${API_URL}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.message || "Ro'yxatdan o'tib bo'lmadi");
  }
  const data = await res.json();
  store(data.access_token, data.role ?? "user");
  return data.access_token as string;
}

export async function fetchMe(): Promise<Me> {
  const res = await fetch(`${API_URL}/api/v1/auth/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error("me failed");
  const me = (await res.json()) as Me;
  localStorage.setItem(ROLE_KEY, me.role);
  return me;
}

export async function logout(): Promise<void> {
  const token = getToken();
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
  if (!token) return;
  try {
    await fetch(`${API_URL}/api/v1/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    /* stateless — mijoz tokeni allaqachon o'chirildi */
  }
}
