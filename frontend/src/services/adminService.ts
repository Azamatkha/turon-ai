// Mock admin xizmati — foydalanuvchilarni localStorage'da boshqaradi (backendsiz).
// Keyinchalik backend ulanganda fetch chaqiruvlariga almashtiriladi.

export type BackendRole = "admin" | "moderator" | "user";

export interface ApiUser {
  id: string;
  username: string;
  full_name: string;
  department: string | null;
  role: BackendRole;
  is_active: boolean;
}

const KEY = "turon_admin_users";

// Boshlang'ich (seed) foydalanuvchilar — birinchi ochilishda localStorage'ga yoziladi
const SEED: ApiUser[] = [
  { id: "1", username: "a.karimov", full_name: "Aziz Karimov", department: "Chakana", role: "user", is_active: true },
  { id: "2", username: "m.yusupova", full_name: "Malika Yusupova", department: "IT", role: "admin", is_active: true },
  { id: "3", username: "d.tashkentov", full_name: "Dilshod Tashkentov", department: "Korporativ", role: "user", is_active: true },
];

// Sun'iy kechikish — yuklash holatlari ko'rinib turishi uchun
const delay = (ms = 250) => new Promise((r) => setTimeout(r, ms));

function read(): ApiUser[] {
  const raw = localStorage.getItem(KEY);
  if (!raw) {
    localStorage.setItem(KEY, JSON.stringify(SEED));
    return [...SEED];
  }
  try {
    return JSON.parse(raw) as ApiUser[];
  } catch {
    return [...SEED];
  }
}

function write(users: ApiUser[]) {
  localStorage.setItem(KEY, JSON.stringify(users));
}

export async function listUsers(search = "", department = ""): Promise<ApiUser[]> {
  await delay();
  let users = read();
  const q = search.trim().toLowerCase();
  if (q) {
    users = users.filter(
      (u) => u.full_name.toLowerCase().includes(q) || u.username.toLowerCase().includes(q)
    );
  }
  if (department) users = users.filter((u) => (u.department || "") === department);
  return users;
}

export async function createUser(input: {
  username: string;
  full_name: string;
  department?: string;
  password: string;
  role: BackendRole;
}): Promise<ApiUser> {
  await delay();
  const users = read();
  if (users.some((u) => u.username.toLowerCase() === input.username.trim().toLowerCase())) {
    throw new Error("Bu login allaqachon band");
  }
  const user: ApiUser = {
    id: "u" + Date.now(),
    username: input.username.trim(),
    full_name: input.full_name.trim(),
    department: input.department?.trim() || null,
    role: input.role,
    is_active: true,
  };
  write([user, ...users]);
  return user;
}

export async function changeRole(id: string, role: BackendRole): Promise<ApiUser> {
  await delay();
  const users = read();
  const user = users.find((u) => u.id === id);
  if (!user) throw new Error("Foydalanuvchi topilmadi");
  user.role = role;
  write(users);
  return user;
}

export async function updateUser(
  id: string,
  input: { username?: string; full_name?: string; department?: string; password?: string }
): Promise<ApiUser> {
  await delay();
  const users = read();
  const user = users.find((u) => u.id === id);
  if (!user) throw new Error("Foydalanuvchi topilmadi");
  if (input.username !== undefined) user.username = input.username.trim();
  if (input.full_name !== undefined) user.full_name = input.full_name.trim();
  if (input.department !== undefined) user.department = input.department.trim() || null;
  write(users);
  return user;
}

export async function deleteUser(id: string): Promise<void> {
  await delay();
  write(read().filter((u) => u.id !== id));
}
