import type { ThemeTokens, SideTokens } from "../../types/chat";

// Chat sahifasidagi xabar-bulutchalari va tugmalarning umumiy aksent rangi
export const ACCENT = "#0B5FA5";

// Turon Bank brend (primary) rangi — logo, mavzu almashtirgich va boshqa
// brend elementlari shu navydan kelib chiqadi. Dark fonda ko'rinishi uchun
// PRIMARY_ON_DARK ishlatiladi.
export const PRIMARY = "#003978";
export const PRIMARY_ON_DARK = "#5FA3D6";

// Asosiy mavzu (light/dark) rang to'plami — ChatHeader, MessageArea, Composer
// shu funksiyadan qaytgan obyektni o'qib, fonni/matn rangini moslashtiradi.
// Bitta joyda turgani uchun light/dark farqi faqat shu yerda boshqariladi.
export function getThemeTokens(isDark: boolean): ThemeTokens {
  return isDark
    ? { bg: "#061A31", headBg: "rgba(6,26,49,.82)", headBorder: "rgba(255,255,255,.08)", strong: "#E2E8F0", muted: "#94A3B8", card: "#0C2949", cardBorder: "rgba(255,255,255,.08)", input: "#E2E8F0", disc: "#64748B", chipShadow: "none" }
    : { bg: "#F8FAFC", headBg: "rgba(248,250,252,.82)", headBorder: "#E2E8F0", strong: "#003978", muted: "#64748B", card: "#ffffff", cardBorder: "#E2E8F0", input: "#003978", disc: "#94A3B8", chipShadow: "0 1px 2px rgba(0, 57, 120,.04)" };
}

// Sidebar uchun alohida token to'plami — sidebar har doim qorong'i fonda turadi
// (mavzudan qat'iy nazar), faqat fon rangi ozgina o'zgaradi (dark mode'da yanada qorong'i)
export function getSideTokens(isDark: boolean): SideTokens {
  return { bg: isDark ? "#072244" : "#003978", fg: "#F1F5F9", sub: "rgba(203,213,225,.55)", active: "rgba(255,255,255,.13)", border: "rgba(255,255,255,.09)", logo: "#5FA3D6", btn: "rgba(255,255,255,.07)" };
}
