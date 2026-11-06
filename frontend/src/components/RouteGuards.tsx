import type { ReactElement } from "react";
import { Navigate } from "react-router-dom";
import { isAuthenticated, isVerified, getRole } from "../services/authService";
import UnverifiedPage from "../pages/UnverifiedPage";

// Login qilmagan foydalanuvchini login sahifasiga yo'naltiradi.
// Tasdiqlanmagan user (mobilda Face-ID'dan o'tmagan) ogohlantirish sahifasini ko'radi.
export function RequireAuth({ children }: { children: ReactElement }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  return isVerified() ? children : <UnverifiedPage />;
}

// Faqat admin uchun; admin bo'lmasa bosh sahifaga qaytaradi
export function RequireAdmin({ children }: { children: ReactElement }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  if (!isVerified()) return <UnverifiedPage />;
  return getRole() === "admin" ? children : <Navigate to="/" replace />;
}
