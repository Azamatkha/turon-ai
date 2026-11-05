// Rollar bo'yicha UI qarorlari. Haqiqiy himoya backendda
// (backend/src/user/auth/permissions/role_matrix.py) — bu yerda faqat
// foydalanuvchiga ruxsati yo'q tugma va bo'limlarni ko'rsatmaymiz.
//
//  * super_admin — hammasi: foydalanuvchilarni tahrirlash, rollar, bilim bazasi;
//  * admin — boshqaruv paneli, foydalanuvchilar va murojaatlarni faqat KO'RADI.
import { getRole } from "../services/authService";
import type { AdminView } from "../types/admin";

export function isPanelRole(role: string | null = getRole()): boolean {
  return role === "super_admin" || role === "admin";
}

export function isSuperAdmin(role: string | null = getRole()): boolean {
  return role === "super_admin";
}

// Oddiy admin ko'radigan admin panel bo'limlari
const ADMIN_VIEWS: AdminView[] = ["dashboard", "users", "reports"];

export function canSeeView(view: AdminView, role: string | null = getRole()): boolean {
  return isSuperAdmin(role) || ADMIN_VIEWS.includes(view);
}
