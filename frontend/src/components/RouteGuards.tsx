import type { ReactElement } from "react";
import { Navigate } from "react-router-dom";
import { isAuthenticated, getRole } from "../services/authService";

// Login qilmagan foydalanuvchini login sahifasiga yo'naltiradi
export function RequireAuth({ children }: { children: ReactElement }) {
  return isAuthenticated() ? children : <Navigate to="/login" replace />;
}

// Faqat admin uchun; admin bo'lmasa bosh sahifaga qaytaradi
export function RequireAdmin({ children }: { children: ReactElement }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  return getRole() === "admin" ? children : <Navigate to="/" replace />;
}
