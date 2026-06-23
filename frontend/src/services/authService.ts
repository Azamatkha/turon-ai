// Mock autentifikatsiya — backendsiz, localStorage asosida ishlaydi.
// Keyinchalik backend ulanganda bu fayldagi funksiyalar haqiqiy fetch chaqiruvlariga almashtiriladi.
// Backend manzili (hozircha ishlatilmaydi, kelajak uchun saqlab qo'yilgan):
export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "turon_token";
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

// Sun'iy kechikish — login/registratsiyada yuklash animatsiyasi ko'rinib turishi uchun
const delay = (ms = 550) => new Promise((r) => setTimeout(r, ms));

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRole(): string | null {
  return localStorage.getItem(ROLE_KEY);
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

// Backend ulanganda foydali bo'ladi (hozir mock servislar buni ishlatmaydi)
export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function store(me: Me) {
  localStorage.setItem(TOKEN_KEY, "mock-" + Math.random().toString(36).slice(2));
  localStorage.setItem(ROLE_KEY, me.role);
  localStorage.setItem(ME_KEY, JSON.stringify(me));
}

// Mock login: "admin" deb kirilsa admin huquqi beriladi, aks holda oddiy xodim.
// Har qanday bo'sh bo'lmagan login/parol qabul qilinadi (backendsiz sinov uchun).
export async function login(loginValue: string, password: string): Promise<string> {
  await delay();
  if (!loginValue.trim() || !password.trim()) throw new Error("Login yoki parol noto'g'ri");
  const isAdmin = loginValue.trim().toLowerCase() === "admin";
  const me: Me = {
    id: "u-" + loginValue.trim().toLowerCase(),
    username: loginValue.trim(),
    email: `${loginValue.trim()}@turonbank.uz`,
    full_name: isAdmin ? "Administrator" : loginValue.trim(),
    department: null,
    role: isAdmin ? "admin" : "user",
  };
  store(me);
  return getToken()!;
}

export async function register(input: {
  username: string;
  full_name: string;
  department?: string;
  password: string;
}): Promise<string> {
  await delay();
  const me: Me = {
    id: "u-" + input.username.toLowerCase(),
    username: input.username,
    email: `${input.username}@turonbank.uz`,
    full_name: input.full_name,
    department: input.department ?? null,
    role: "user",
  };
  store(me);
  return getToken()!;
}

export async function fetchMe(): Promise<Me> {
  const raw = localStorage.getItem(ME_KEY);
  if (!raw) throw new Error("me failed");
  return JSON.parse(raw) as Me;
}

export async function logout(): Promise<void> {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(ME_KEY);
}
