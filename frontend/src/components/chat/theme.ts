import type { ThemeTokens, SideTokens } from "../../types/chat";

// Chat sahifasidagi xabar-bulutchalari va tugmalarning umumiy aksent rangi
export const ACCENT = "#2563EB";

// Turon Bank brend (primary) rangi — logo, mavzu almashtirgich va boshqa
// brend elementlari shu navydan kelib chiqadi. Dark fonda ko'rinishi uchun
// PRIMARY_ON_DARK ishlatiladi.
export const PRIMARY = "#1E3A5F";
export const PRIMARY_ON_DARK = "#60A5FA";

// Asosiy mavzu (light/dark) rang to'plami — ChatHeader, MessageArea, Composer
// shu funksiyadan qaytgan obyektni o'qib, fonni/matn rangini moslashtiradi.
// Bitta joyda turgani uchun light/dark farqi faqat shu yerda boshqariladi.
export function getThemeTokens(isDark: boolean): ThemeTokens {
  return isDark
    ? { bg: "#0B1524", headBg: "rgba(11,21,36,.82)", headBorder: "rgba(255,255,255,.08)", strong: "#E2E8F0", muted: "#94A3B8", card: "#152741", cardBorder: "rgba(255,255,255,.08)", input: "#E2E8F0", disc: "#64748B", chipShadow: "none" }
    : { bg: "#F8FAFC", headBg: "rgba(248,250,252,.82)", headBorder: "#E2E8F0", strong: "#1E3A5F", muted: "#64748B", card: "#ffffff", cardBorder: "#E2E8F0", input: "#1E3A5F", disc: "#94A3B8", chipShadow: "0 1px 2px rgba(30, 58, 95,.04)" };
}

// Sidebar uchun alohida token to'plami — sidebar har doim qorong'i fonda turadi
// (mavzudan qat'iy nazar), faqat fon rangi ozgina o'zgaradi (dark mode'da yanada qorong'i)
export function getSideTokens(isDark: boolean): SideTokens {
  return { bg: isDark ? "#122036" : "#1E3A5F", fg: "#F1F5F9", sub: "rgba(203,213,225,.55)", active: "rgba(255,255,255,.13)", border: "rgba(255,255,255,.09)", logo: "#60A5FA", btn: "rgba(255,255,255,.07)" };
}
