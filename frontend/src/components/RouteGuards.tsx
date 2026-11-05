import type { ReactElement } from "react";
import { Navigate } from "react-router-dom";
import { isAuthenticated, isVerified } from "../services/authService";
import { isPanelRole } from "../utils/roles";
import UnverifiedPage from "../pages/UnverifiedPage";

// Login qilmagan foydalanuvchini login sahifasiga yo'naltiradi.
// Tasdiqlanmagan user (mobilda Face-ID'dan o'tmagan) ogohlantirish sahifasini ko'radi.
export function RequireAuth({ children }: { children: ReactElement }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  return isVerified() ? children : <UnverifiedPage />;
}

// Faqat admin va super admin uchun; boshqalar bosh sahifaga qaytadi
export function RequireAdmin({ children }: { children: ReactElement }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  if (!isVerified()) return <UnverifiedPage />;
  return isPanelRole() ? children : <Navigate to="/" replace />;
}
