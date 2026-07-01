// Haqiqiy autentifikatsiya — backendga ulangan (FastAPI, JWT access+refresh token).
export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "turon_token";
const REFRESH_KEY = "turon_refresh";
const ROLE_KEY = "turon_role";
const ME_KEY = "turon_me";

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

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
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

function storeTokens(t: { access_token: string; refresh_token: string }) {
  localStorage.setItem(TOKEN_KEY, t.access_token);
  localStorage.setItem(REFRESH_KEY, t.refresh_token);
}

function clearStorage() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(ME_KEY);
}

async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json();
    const d = data.detail ?? data.message;
    // FastAPI validatsiya xatolari massiv ko'rinishida keladi
    if (Array.isArray(d)) {
      return d.map((e) => e?.msg || e?.message || String(e)).join("; ") || fallback;
    }
    if (typeof d === "string") return d;
    return fallback;
  } catch {
    return fallback;
  }
}

// Avtorizatsiyalangan so'rov: 401 bo'lsa refresh token bilan bir marta qayta uradi
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const doFetch = () =>
    fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...authHeaders(), ...(init.headers || {}) },
    });

  let res = await doFetch();
  if (res.status === 401 && getRefreshToken()) {
    const ok = await tryRefresh();
    if (ok) res = await doFetch();
    else clearStorage();
  }
  return res;
}

async function tryRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_URL}/v1/users/auth/login/refresh`, {
      method: "POST",
      headers: { Authorization: `Bearer ${refresh}` },
    });
    if (!res.ok) return false;
    storeTokens(await res.json());
    return true;
  } catch {
    return false;
  }
}

export async function login(loginValue: string, password: string): Promise<string> {
  const res = await fetch(`${API_URL}/v1/users/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: loginValue.trim().toLowerCase(), password }),
  });
  if (!res.ok) throw new Error(await readError(res, "Login yoki parol noto'g'ri"));
  storeTokens(await res.json());
  await fetchMe();
  return getToken()!;
}

export async function register(input: {
  username: string;
  full_name: string;
  department?: string;
  password: string;
}): Promise<string> {
  const res = await fetch(`${API_URL}/v1/users/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      full_name: input.full_name,
      username: input.username,
      department: input.department ?? null,
      password: input.password,
    }),
  });
  if (!res.ok) throw new Error(await readError(res, "Ro'yxatdan o'tishda xatolik"));
  return login(input.username, input.password);
}

export async function fetchMe(): Promise<Me> {
  const res = await apiFetch("/v1/users/me");
  if (!res.ok) throw new Error(await readError(res, "Profilni olishda xatolik"));
  const u = await res.json();
  const me: Me = {
    id: u.id,
    username: u.username,
    email: u.email,
    full_name: u.full_name,
    department: u.department ?? null,
    role: u.role,
  };
  localStorage.setItem(ROLE_KEY, me.role);
  localStorage.setItem(ME_KEY, JSON.stringify(me));
  return me;
}

export async function logout(): Promise<void> {
  try {
    await apiFetch("/v1/users/auth/logout", { method: "POST", body: JSON.stringify({}) });
  } catch {
    // tarmoq xatosi bo'lsa ham mahalliy tozalaymiz
  }
  clearStorage();
}

// Foydalanuvchi o'z parolini o'zgartiradi (kuchli parol talab qilinadi)
export async function changePassword(newPassword: string): Promise<void> {
  const res = await apiFetch("/v1/users/me/password", {
    method: "PATCH",
    body: JSON.stringify({ password: newPassword }),
  });
  if (!res.ok) throw new Error(await readError(res, "Parolni o'zgartirishda xatolik"));
}