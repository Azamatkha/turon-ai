import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
// Asosiy shrift — loyiha ichidan (Google Fonts bank proksisi ortida ochilmaydi).
// Variable versiya: barcha qalinliklar bitta faylda, alohida wght so'rovi yo'q.
import "@fontsource-variable/onest";
import "./index.css";
// Butun flag-icons paketi EMAS — faqat ilovada ishlatiladigan 13 ta bayroq.
// Sabab va yangi bayroq qo'shish tartibi: styles/flags.css boshidagi izoh.
import "./styles/flags.css";
import { ThemeProvider } from "./contexts/ThemeContext";
import LoginPage from "./pages/LoginPage";
import ChatPage from "./pages/ChatPage";
import AdminPage from "./pages/AdminPage";
import NotFoundPage from "./pages/NotFoundPage";
import { RequireAuth, RequireAdmin } from "./components/RouteGuards";

// Marshrutlar: "/" = chat (login bo'lsa), aks holda login sahifasiga yo'naltiradi
const router = createBrowserRouter([
  { path: "/", element: <RequireAuth><ChatPage /></RequireAuth> },
  { path: "/c/:sessionId", element: <RequireAuth><ChatPage /></RequireAuth> },
  { path: "/login", element: <LoginPage /> },
  // Saytdan ro'yxatdan o'tish YOPILDI — ro'yxatdan o'tish faqat mobil ilovada
  // (yuzni tasdiqlash kamera va FaceID SDK talab qiladi). Manzilni qo'lda
  // yozib kirmoqchi bo'lganlar login sahifasiga qaytariladi.
  // RegisterPage/RegisterForm fayllari o'chirilmadi — mobil oqim ishga
  // tushgach kerak bo'lishi mumkin.
  { path: "/register", element: <Navigate to="/login" replace /> },
  { path: "/chat", element: <Navigate to="/" replace /> },
  { path: "/admin", element: <RequireAdmin><AdminPage /></RequireAdmin> },
  // Admin ichidagi sahifa manzilda saqlanadi — refresh qilinganda o'sha sahifa ochiladi
  { path: "/admin/:view", element: <RequireAdmin><AdminPage /></RequireAdmin> },
  { path: "*", element: <NotFoundPage /> },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <RouterProvider router={router} />
    </ThemeProvider>
  </React.StrictMode>
);
