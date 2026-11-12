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
  first_name: string;
  last_name: string;
  department: string | null;
  role: string;
  // Mobil ilovada Face-ID verifikatsiyasidan o'tganmi
  is_verified: boolean;
  // Verifikatsiyadan kelgan ma'lumotlar (eski userlarda bo'sh)
  patronym: string | null;
  pnfl: string | null;
  doc_seria: string | null;
  doc_number: string | null;
  birth_date: string | null;
  position: string | null;
  // Kontaktlar — ixtiyoriy, foydalanuvchi o'zi kiritadi (PATCH /me/contacts).
  // phone_number: "+998991234567"; ip_number: 1-4 xonali ichki raqam.
  phone_number: string | null;
  ip_number: string | null;
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

// Tasdiqlanmagan user saytda faqat ogohlantirish sahifasini ko'radi.
// Profil hali saqlanmagan (yoki eski formatda) bo'lsa — to'smaymiz: backend
// baribir tasdiqlanmagan userga chat va boshqa API'larni 403 bilan yopadi.
export function isVerified(): boolean {
  try {
    const me = JSON.parse(localStorage.getItem(ME_KEY) || "null");
    return me?.is_verified !== false;
  } catch {
    return true;
  }
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

// HTTP status kodini saqlab qoladi — chaqiruvchi tomon (masalan LoginPage) xato turini
// (429 — juda ko'p urinish, 409 — allaqachon mavjud) matndan emas, kod orqali aniqlay oladi.
// Login javobidagi is_verified=false — LoginPage buni alohida ko'rsatadi
export const UNVERIFIED_STATUS = 403;

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

// Backend xato matni. FastAPI validatsiya xatolari (422) massiv bo'lib keladi —
// ularni o'qiladigan matnga aylantiramiz, aks holda "[object Object]" chiqardi.
export async function readApiError(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json();
    const d = data?.detail ?? data?.message;
    if (Array.isArray(d)) {
      return (
        d
          .map((e) => {
            const msg = String(e?.msg || e?.message || "").replace(/^Value error,\s*/i, "");
            const field = Array.isArray(e?.loc) ? e.loc[e.loc.length - 1] : "";
            return field && typeof field === "string" ? `${field}: ${msg}` : msg;
          })
          .filter(Boolean)
          .join("; ") || fallback
      );
    }
    if (typeof d === "string" && d) return d;
    return fallback;
  } catch {
    return fallback;
  }
}



// Avtorizatsiyalangan so'rov: 401 bo'lsa refresh token bilan bir marta qayta uradi
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  // FormData (fayl yuklash) bo'lsa Content-Type'ni brauzerning o'zi (boundary bilan) qo'yadi —
  // shuning uchun majburan "application/json" bermaymiz. Qolgan hollarda avvalgidek JSON.
  const isForm = init.body instanceof FormData;
  const baseHeaders: Record<string, string> = isForm ? {} : { "Content-Type": "application/json" };
  const doFetch = () =>
    fetch(`${API_URL}${path}`, {
      ...init,
      headers: { ...baseHeaders, ...authHeaders(), ...(init.headers || {}) },
    });

  const hadSession = isAuthenticated();
  let res = await doFetch();
  let refreshUnavailable = false;
  if (res.status === 401 && getRefreshToken()) {
    const outcome = await refreshOnce();
    if (outcome === "ok") res = await doFetch();
    // Tarmoq/5xx/429 — sessiya tugagani emas: tokenlar qoladi, keyingi so'rov qayta urinadi
    else if (outcome === "rejected") clearStorage();
    else refreshUnavailable = true;
  }
  // Sessiya tugadi (refresh ham rad etildi) — "401" xatosini ko'rsatmay,
  // to'g'ridan-to'g'ri umumiy login sahifasiga o'tamiz. Chaqiruvchiga hech
  // narsa qaytmaydi (promise osilib qoladi) — sahifa baribir almashadi va
  // ekranda bir lahza ham xato yozuvi chiqmaydi.
  if (res.status === 401 && hadSession && !refreshUnavailable && path !== LOGOUT_PATH) {
    redirectToLogin();
    return new Promise<Response>(() => {});
  }
  if (res.status === 403 && path !== "/v1/users/me") void recheckVerification();
  return res;
}

const LOGOUT_PATH = "/v1/users/auth/logout";

// Bir nechta so'rov bir vaqtda 401 olsa — faqat bitta yo'naltirish
let redirectingToLogin = false;
function redirectToLogin(): void {
  if (redirectingToLogin) return;
  redirectingToLogin = true;
  clearStorage();
  goToLogin();
}

// Admin userning tasdiqini olib tashlasa, brauzerdagi saqlangan profil hali
// "tasdiqlangan" deb turadi va chat sahifasi 403 olib turaveradi. 403 kelganda
// profil qayta o'qiladi; user tasdiqlanmagan bo'lsa sahifa yangilanib,
// ogohlantirish oynasi (UnverifiedPage) chiqadi.
let recheckingVerification = false;
async function recheckVerification(): Promise<void> {
  if (recheckingVerification || !isVerified()) return;
  recheckingVerification = true;
  try {
    const me = await fetchMe();
    if (!me.is_verified) window.location.reload();
  } catch {
    // tarmoq xatosi — keyingi 403 da qayta tekshiriladi
  } finally {
    recheckingVerification = false;
  }
}

type RefreshOutcome = "ok" | "rejected" | "unavailable";

const HTTP_TOO_MANY_REQUESTS = 429;
const HTTP_SERVER_ERROR_MIN = 500;

async function requestRefresh(): Promise<RefreshOutcome> {
  const refresh = getRefreshToken();
  if (!refresh) return "rejected";
  let res: Response;
  try {
    res = await fetch(`${API_URL}/v1/users/auth/login/refresh`, {
      method: "POST",
      headers: { Authorization: `Bearer ${refresh}` },
    });
  } catch {
    return "unavailable";
  }
  if (res.ok) {
    storeTokens(await res.json());
    return "ok";
  }
  if (res.status === HTTP_TOO_MANY_REQUESTS || res.status >= HTTP_SERVER_ERROR_MIN) return "unavailable";
  // Boshqa vkladka shu orada tokenni yangilagan bo'lsa — rad etilgani eski token
  return getRefreshToken() !== refresh ? "ok" : "rejected";
}

let refreshInflight: Promise<RefreshOutcome> | null = null;

// Bir vaqtda kelgan bir nechta 401 bitta refresh'ni kutadi: refresh token bir
// martalik, parallel so'rovlar bir-birining yangi tokenini o'chirib yuborardi.
function refreshOnce(): Promise<RefreshOutcome> {
  if (!refreshInflight) {
    refreshInflight = requestRefresh().finally(() => {
      refreshInflight = null;
    });
  }
  return refreshInflight;
}

// ── Turon ID (bankning yagona kirishi) ───────────────────────────────────
// Portal chatni bir martalik kod bilan ochadi: https://…/chat/#sso=<kod>.
// Kod fragmentda keladi (serverga, loglarga va Referer'ga tushmaydi); backend
// uni Turon ID bilan almashtiradi va oddiy chat sessiyasini qaytaradi.
const SSO_FRAGMENT = "sso";
const SSO_ERROR_KEY = "turon_sso_error";

// Turon AI portalidagi platformalar sahifasi (chatdan "orqaga" havolasi uchun)
export function platformsUrl(): string | null {
  const portal = import.meta.env.VITE_TURON_PORTAL_URL;
  return portal ? `${portal.replace(/\/$/, "")}/platforms` : null;
}

export async function signInWithTuronId(code: string): Promise<void> {
  const res = await fetch(`${API_URL}/v1/users/auth/turon-id`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  if (!res.ok) throw new ApiError(await readApiError(res, "Turon ID orqali kirib bo'lmadi"), res.status);
  // Yangi sessiya: oldingi foydalanuvchining saqlangan profili qolmasin
  clearStorage();
  storeTokens(await res.json());
  await fetchMe();
}

/**
 * Manzilda #sso=<kod> bo'lsa — uni darhol o'chiradi (tarixda qolmasin) va
 * kirishni bajaradi. Xato bo'lsa, login sahifasi ko'rsatishi uchun belgilab qo'yadi.
 */
export async function consumeTuronIdCode(): Promise<void> {
  const params = new URLSearchParams(window.location.hash.slice(1));
  const code = params.get(SSO_FRAGMENT);
  if (!code) return;
  window.history.replaceState(null, "", window.location.pathname + window.location.search);
  try {
    // Mavjud sessiya faqat yangisi kelganda almashtiriladi (storeTokens):
    // kod o'tmasa, foydalanuvchi oldingi sessiyasida qoladi.
    await signInWithTuronId(code);
    sessionStorage.removeItem(SSO_ERROR_KEY);
  } catch {
    sessionStorage.setItem(SSO_ERROR_KEY, "1");
  }
}

/** Turon ID orqali kirish muvaffaqiyatsiz tugadimi (bir marta o'qiladi). */
export function takeTuronIdError(): boolean {
  const failed = sessionStorage.getItem(SSO_ERROR_KEY) === "1";
  sessionStorage.removeItem(SSO_ERROR_KEY);
  return failed;
}

export async function login(loginValue: string, password: string): Promise<string> {
  const res = await fetch(`${API_URL}/v1/users/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: loginValue.trim(), password }),
  });
  if (!res.ok) throw new ApiError(await readApiError(res, "Login yoki parol noto'g'ri"), res.status);
  const data = await res.json();
  // Tasdiqlanmagan userga backend access/refresh bermaydi (faqat mobil
  // Face-ID uchun token + p12). Web'da u baribir chatga kira olmaydi —
  // login sahifasining o'zida "tasdiqlanmagan" xabari ko'rsatiladi.
  if (data.is_verified === false) {
    throw new ApiError("unverified", UNVERIFIED_STATUS);
  }
  storeTokens(data);
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
  if (!res.ok) throw new ApiError(await readApiError(res, "Ro'yxatdan o'tishda xatolik"), res.status);
  return login(input.username, input.password);
}

// Backend profil javobini `Me` ga o'giradi va brauzerda saqlaydi. Ilgari bu
// uch joyda qo'lda takrorlanardi — yangi maydon qo'shilganda biri eskirib
// qolish xavfi bor edi.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function storeMe(u: any): Me {
  const me: Me = {
    id: u.id,
    username: u.username,
    email: u.email,
    full_name: u.full_name,
    first_name: u.first_name ?? "",
    last_name: u.last_name ?? "",
    department: u.department ?? null,
    role: u.role,
    is_verified: u.is_verified ?? true,
    patronym: u.patronym ?? null,
    pnfl: u.pnfl ?? null,
    doc_seria: u.doc_seria ?? null,
    doc_number: u.doc_number ?? null,
    birth_date: u.birth_date ?? null,
    position: u.position ?? null,
    phone_number: u.phone_number ?? null,
    ip_number: u.ip_number ?? null,
  };
  localStorage.setItem(ROLE_KEY, me.role);
  localStorage.setItem(ME_KEY, JSON.stringify(me));
  return me;
}

export async function fetchMe(): Promise<Me> {
  const res = await apiFetch("/v1/users/me");
  if (!res.ok) throw new Error(await readApiError(res, "Profilni olishda xatolik"));
  const u = await res.json();
  return storeMe(u);
}

// Tasdiqlanmagan sahifada: profil backend'dan qayta o'qiladi (localStorage'dagi
// eski nusxa yangilanadi). User mobilda verifikatsiyadan o'tgan bo'lsa — true.
// Busiz eski `is_verified:false` F5'dan keyin ham qolib, faqat qayta login yordam berardi.
export async function recheckVerified(): Promise<boolean> {
  if (!isAuthenticated()) return false;
  try {
    return (await fetchMe()).is_verified;
  } catch {
    return false;
  }
}

// Chiqishdan keyin o'tiladigan sahifa — Turon AI portalining logini
// (chatning o'z /login sahifasi emas)
export const PORTAL_LOGIN_URL = "https://turon-ai.turonbank.uz/login";

// Login qilinmagan / sessiya tugagan foydalanuvchini login'ga jo'natadi.
// Prod'da — portal logini; chatning o'z sahifasi (/chat/login) faqat manzilni
// qo'lda yozganda ochiladi. Lokal `npm run dev` da portal yo'q — o'z /login.
export function goToLogin(): void {
  if (import.meta.env.DEV) window.location.assign(`${import.meta.env.BASE_URL}login`);
  else window.location.replace(PORTAL_LOGIN_URL);
}

export async function logout(): Promise<void> {
  try {
    await apiFetch("/v1/users/auth/logout", { method: "POST", body: JSON.stringify({}) });
  } catch {
    // tarmoq xatosi bo'lsa ham mahalliy tozalaymiz
  }
  clearStorage();
}

// Foydalanuvchi o'z ismini/loginini o'zgartiradi.
// Backend `user_id` ni TOKENDAN oladi, shuning uchun bu yerda id yuborilmaydi.
export async function updateProfile(input: {
  full_name?: string;
  username?: string;
}): Promise<Me> {
  const res = await apiFetch("/v1/users/me", {
    method: "PATCH",
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    throw new ApiError(await readApiError(res, "Profilni saqlashda xatolik"), res.status);
  }
  const u = await res.json();
  return storeMe(u);
}


// Foydalanuvchi o'z telefon va IP (ichki) raqamini kiritadi/o'zgartiradi.
// Yuborilmagan maydon o'zgarmaydi; bo'sh satr ("") raqamni o'chiradi.
// Backend raqamni tekshirib, "+998991234567" ko'rinishida saqlaydi.
export async function updateContacts(input: {
  phone_number?: string;
  ip_number?: string;
}): Promise<Me> {
  const res = await apiFetch("/v1/users/me/contacts", {
    method: "PATCH",
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    throw new ApiError(await readApiError(res, "Raqamlarni saqlashda xatolik"), res.status);
  }
  return storeMe(await res.json());
}

// Foydalanuvchi o'z parolini o'zgartiradi — faqat yangi parol (joriy parol
// so'ralmaydi, backend `UserNewPassword` docstring'iga qarang).
// Muvaffaqiyatli o'zgarishdan keyin backend BARCHA sessiyalarni bekor qiladi,
// shuning uchun chaqiruvchi tomon foydalanuvchini qayta login qilishga
// yuborishi kerak.
export async function changePassword(newPassword: string): Promise<void> {
  const res = await apiFetch("/v1/users/me/password", {
    method: "PATCH",
    body: JSON.stringify({ password: newPassword }),
  });
  if (!res.ok) {
    throw new ApiError(
      await readApiError(res, "Parolni o'zgartirishda xatolik"),
      res.status,
    );
  }
}
// ---- Faol seanslar — /v1/users/auth/sessions ----

export interface ActiveSession {
  session_id: string;
  // "Chrome · Windows", "Turon AI app · Android"; noma'lum bo'lsa ""
  device: string;
  user_agent: string;
  ip: string;
  created_at?: string | null;
  last_seen_at?: string | null;
  // Shu brauzerdagi seans
  current: boolean;
}

export async function listActiveSessions(): Promise<ActiveSession[]> {
  const res = await apiFetch("/v1/users/auth/sessions");
  if (!res.ok) throw new Error(await readApiError(res, "Seanslarni olishda xatolik"));
  return res.json();
}

export async function revokeSession(sessionId: string): Promise<void> {
  const res = await apiFetch(`/v1/users/auth/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await readApiError(res, "Seansni yopib bo'lmadi"));
}

// Joriy brauzerdan tashqari hamma qurilmalardan chiqish; nechta yopilganini qaytaradi
export async function revokeOtherSessions(): Promise<number> {
  const res = await apiFetch("/v1/users/auth/sessions/revoke-others", { method: "POST" });
  if (!res.ok) throw new Error(await readApiError(res, "Seanslarni yopib bo'lmadi"));
  return ((await res.json()) as { revoked: number }).revoked;
}
