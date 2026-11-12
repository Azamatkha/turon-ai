import { useEffect, type ReactElement } from "react";
import { Navigate } from "react-router-dom";
import { isAuthenticated, isVerified, getRole, goToLogin } from "../services/authService";
import UnverifiedPage from "../pages/UnverifiedPage";

// Login qilmagan foydalanuvchi (masalan /chat/ ni to'g'ridan-to'g'ri ochgan)
// portal login sahifasiga yuboriladi — chatning o'z /login sahifasiga emas.
function LoginRedirect() {
  useEffect(() => {
    goToLogin();
  }, []);
  return null;
}

// Tasdiqlanmagan user (mobilda Face-ID'dan o'tmagan) ogohlantirish sahifasini ko'radi.
export function RequireAuth({ children }: { children: ReactElement }) {
  if (!isAuthenticated()) return <LoginRedirect />;
  return isVerified() ? children : <UnverifiedPage />;
}

// Faqat admin uchun; admin bo'lmasa bosh sahifaga qaytaradi
export function RequireAdmin({ children }: { children: ReactElement }) {
  if (!isAuthenticated()) return <LoginRedirect />;
  if (!isVerified()) return <UnverifiedPage />;
  return getRole() === "admin" ? children : <Navigate to="/" replace />;
}
